# 📊 Guide complet du Monitoring et des Alertes - FlaskFolio

Ce document explique l'architecture complète du système de monitoring et d'alertes mis en place pour surveiller les jobs cron de l'application FlaskFolio.

---

## 🏗️ Architecture globale

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLUX DE MONITORING                          │
└─────────────────────────────────────────────────────────────────┘

    Jobs Cron                    Métriques                  Visualisation
    (manage.py)                                            & Alertes
         │                                                      │
         │  1. Exécution                                       │
         ├──────────────────────────┐                          │
         │                          │                          │
         │  2. Push métriques       │                          │
         ▼                          ▼                          │
  ┌─────────────┐          ┌──────────────┐                   │
  │ Metrics     │          │ Pushgateway  │                   │
  │ Handler     ├─────────►│   :9091      │                   │
  │ (Python)    │          │              │                   │
  └─────────────┘          └──────┬───────┘                   │
                                  │                           │
                                  │ 3. Scrape                 │
                                  ▼                           │
                           ┌──────────────┐                   │
                           │ Prometheus   │                   │
                           │   :9090      │                   │
                           │              │                   │
                           │ - Scraping   │                   │
                           │ - Evaluation │                   │
                           │   des règles │                   │
                           └──────┬───────┘                   │
                                  │                           │
                    ┌─────────────┼─────────────┐            │
                    │             │             │            │
                    │ 4a. Alertes │ 4b. Query   │            │
                    ▼             ▼             ▼            │
            ┌──────────────┐  ┌──────────────┐             │
            │Alertmanager  │  │   Grafana    │◄────────────┘
            │   :9093      │  │   :3000      │  5. Affichage
            │              │  │              │
            │ - Routing    │  │ - Dashboards │
            │ - Grouping   │  │ - Panels     │
            │ - Notification│  │              │
            └──────────────┘  └──────────────┘
                    │
                    │ 6. Notifications
                    ▼
            Email / Webhook
```

---

## 📁 Structure des fichiers

### 1️⃣ **Code applicatif**

#### `pea_trading/utils/metrics.py`
**Rôle** : Module Python qui gère l'envoi des métriques vers le Pushgateway.

**Contenu clé** :
```python
class MetricsHandler:
    def push_job_metrics(self, job_name, success, duration, records, error_message):
        """
        Pousse 5 types de métriques vers le Pushgateway :
        - cron_job_success : 1 = succès, 0 = échec
        - cron_job_duration_seconds : Temps d'exécution
        - cron_job_records_processed : Nombre d'enregistrements
        - cron_job_last_execution_timestamp : Timestamp Unix
        - cron_job_error : Message d'erreur si échec
        """
```

**Utilisation dans le code** :
```python
# Dans manage.py, chaque commande est instrumentée
from pea_trading.utils.metrics import metrics_handler

@cli.command("export_transactions_csv")
def export_transactions_csv(portfolio_name, output):
    start_time = time.time()
    success = False
    records = 0
    job_name = f"export_transactions_{portfolio_name.replace(' ', '_')}"
    
    try:
        # Logique du job
        records = len(portfolio.transactions)
        success = True
    except Exception as e:
        error_message = str(e)
    finally:
        duration = time.time() - start_time
        metrics_handler.push_job_metrics(
            job_name=job_name,
            success=success,
            duration=duration,
            records=records,
            error_message=error_message
        )
```

**Méthode de push** : Utilise `pushadd_to_gateway()` avec un `grouping_key` pour que chaque job ait ses métriques isolées.

---

### 2️⃣ **Pushgateway**

#### Service Docker : `pushgateway:9091`

**Rôle** : Point d'entrée pour les métriques des jobs batch/cron.

**Pourquoi nécessaire ?** :
- Les jobs cron sont éphémères (ils ne tournent pas en continu)
- Prometheus ne peut pas les scraper directement
- Le Pushgateway stocke temporairement les métriques

**Configuration** : Pas de fichier de config, juste le service Docker.

**Vérification** :
```bash
# Voir les métriques stockées
curl http://localhost:9091/metrics | grep cron_job

# Supprimer toutes les métriques
curl -X DELETE http://localhost:9091/metrics/job/cron_jobs
```

---

### 3️⃣ **Prometheus**

#### Fichier : `prometheus/prometheus.yml`

**Rôle** : Configuration du serveur Prometheus.

**Sections importantes** :

```yaml
global:
  scrape_interval: 15s        # Scrape les targets toutes les 15s
  evaluation_interval: 1m     # Évalue les règles d'alertes toutes les minutes

# Fichiers de règles d'alertes
rule_files:
  - /etc/prometheus/alerts.yml

# Configuration Alertmanager
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

scrape_configs:
  # Scrape l'application Flask
  - job_name: 'flask-app'
    static_configs:
      - targets: ['web:5000']
  
  # Scrape le Pushgateway
  - job_name: 'pushgateway'
    honor_labels: true          # Préserve les labels des jobs
    static_configs:
      - targets: ['pushgateway:9091']
```

**Points clés** :
- `honor_labels: true` : Important pour garder les labels `job_name` poussés par les jobs
- `evaluation_interval: 1m` : Les alertes sont évaluées toutes les minutes

#### Fichier : `prometheus/alerts.yml`

**Rôle** : Définition des 8 règles d'alertes.

**Structure d'une alerte** :
```yaml
- alert: CronJobFailed                    # Nom de l'alerte
  expr: cron_job_success == 0             # Condition PromQL
  for: 2m                                 # Délai avant déclenchement
  labels:
    severity: critical                    # Niveau de sévérité
    component: cron
  annotations:
    summary: "Job {{ $labels.job_name }} a échoué"
    description: "Détails de l'alerte..."
```

**Les 8 alertes configurées** :

| Alerte | Expression PromQL | Délai | Sévérité |
|--------|-------------------|-------|----------|
| **CronJobFailed** | `cron_job_success == 0` | 2m | critical |
| **CronJobTooSlow** | `cron_job_duration_seconds > 60` | 1m | warning |
| **CronJobHistoryTooSlow** | `cron_job_duration_seconds{job_name="export_all_stock_history"} > 120` | 1m | warning |
| **CronJobNotExecutedFor8Days** | `(time() - cron_job_last_execution_timestamp) > 691200` | 5m | warning |
| **CronJobNotExecutedFor2Weeks** | `(time() - cron_job_last_execution_timestamp) > 1209600` | 5m | critical |
| **CronJobNoRecordsProcessed** | `cron_job_success == 1 and cron_job_records_processed == 0` | 5m | warning |
| **AllCronJobsFailed** | `count(cron_job_success == 0) >= 3` | 5m | critical |
| **CronJobStuckRunning** | `(time() - cron_job_last_execution_timestamp) < 60 and cron_job_duration_seconds > 300` | 10m | warning |

**Accès web** : http://localhost:9090
- `/rules` : Liste des règles chargées
- `/alerts` : Alertes actives
- `/graph` : Explorer les métriques avec PromQL

---

### 4️⃣ **Alertmanager**

#### Fichier : `alertmanager/config.yml`

**Rôle** : Gestion intelligente des alertes (routing, grouping, notifications).

**Structure** :

```yaml
global:
  resolve_timeout: 5m

# Routing principal
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'severity', 'component']
  group_wait: 10s              # Attente avant envoi
  group_interval: 5m           # Intervalle entre groupes
  repeat_interval: 4h          # Répétition si non résolue
  
  # Routes spécifiques
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 0s             # Envoi immédiat
      repeat_interval: 1h
    
    - match:
        severity: warning
      receiver: 'warning-alerts'
      repeat_interval: 4h

# Inhibition : évite les doublons
inhibit_rules:
  - source_match:
      alertname: 'AllCronJobsFailed'
    target_match:
      alertname: 'CronJobFailed'
    equal: ['component']

# Receivers : comment envoyer
receivers:
  - name: 'critical-alerts'
    webhook_configs:
      - url: 'http://localhost:5001/webhook/critical'
    # email_configs:  # À décommenter pour activer
    #   - to: 'admin@example.com'
    #     from: 'alertmanager@example.com'
    #     smarthost: 'smtp.gmail.com:587'
    #     auth_username: 'your-email@gmail.com'
    #     auth_password: 'your-app-password'
```

**Fonctionnalités clés** :
- **Grouping** : Regroupe les alertes similaires en un seul message
- **Routing** : Dirige les alertes vers différents receivers selon la sévérité
- **Inhibition** : Supprime les alertes redondantes
- **Repeat** : Répète les notifications si non résolues

**Configuration email** : Décommenter et personnaliser la section `email_configs` avec vos identifiants SMTP.

**Accès web** : http://localhost:9093
- Liste des alertes reçues
- Gestion du silence (mute) des alertes

---

### 5️⃣ **Grafana**

#### Fichier : `grafana/provisioning/dashboards/grafana-dashboard-cron-jobs.json`

**Rôle** : Dashboard de visualisation des métriques des jobs cron.

**Structure** :
```json
{
  "title": "Cron Jobs Monitoring",
  "timezone": "browser",
  "refresh": "30s",
  "panels": [
    {
      "title": "Last Job Status",
      "type": "stat",
      "targets": [{"expr": "cron_job_success"}],
      "fieldConfig": {
        "mappings": [
          {"value": "1", "text": "✅ SUCCESS"},
          {"value": "0", "text": "❌ FAILED"}
        ]
      }
    },
    {
      "title": "Last Execution Status",
      "type": "table",
      "targets": [
        {"expr": "max by (job_name) (cron_job_success)", "refId": "A"},
        {"expr": "max by (job_name) (cron_job_duration_seconds)", "refId": "B"},
        {"expr": "max by (job_name) (cron_job_records_processed)", "refId": "C"},
        {"expr": "max by (job_name) (cron_job_last_execution_timestamp * 1000)", "refId": "D"}
      ]
    }
    // ... 3 autres panneaux
  ]
}
```

**Les 5 panneaux du dashboard** :

1. **Last Job Status** (stat) :
   - Affiche le statut actuel (✅/❌) de chaque job
   - Type : Panneau stat avec fond coloré (vert/rouge)

2. **Last Execution Status** (table) :
   - Tableau récapitulatif avec 4 colonnes : Success, Duration, Records, Last Execution
   - Utilise `max by (job_name)` pour grouper les métriques

3. **Job Execution Duration** (timeseries) :
   - Graphique temporel de la durée d'exécution
   - Permet de voir les tendances et pics

4. **Records Processed per Job** (timeseries en barres) :
   - Volume de données traitées par job
   - Affichage en barres pour faciliter la comparaison

5. **Job Execution Timeline** (state-timeline) :
   - Timeline visuelle succès/échecs
   - Bandes vertes (succès) / rouges (échecs)

**Requêtes PromQL utilisées** :
```promql
# Statut actuel
cron_job_success

# Agrégation par job
max by (job_name) (cron_job_success)

# Durée
cron_job_duration_seconds

# Records
cron_job_records_processed

# Timestamp (converti en millisecondes pour Grafana)
cron_job_last_execution_timestamp * 1000
```

**Import du dashboard** :
1. Aller sur http://localhost:3000
2. Dashboards → Import
3. Copier/coller le contenu du fichier JSON
4. Sélectionner Prometheus comme datasource
5. Import

**Accès** : http://localhost:3000
- Login par défaut : admin/admin

---

## 🔄 Flux de données détaillé

### 1. **Exécution d'un job cron** (Samedi 8h00)

```bash
# Crontab déclenche la commande
0 8 * * 6 cd /app && python3 manage.py export_transactions_csv "PEA"
```

### 2. **Instrumentation dans le code**

```python
# manage.py - Début du job
start_time = time.time()
job_name = "export_transactions_PEA"

try:
    # Logique métier
    portfolio.export_transactions()
    records = len(portfolio.transactions)  # 23 transactions
    success = True
    
except Exception as e:
    success = False
    error_message = str(e)
    
finally:
    duration = time.time() - start_time  # 0.014s
    
    # Push vers Pushgateway
    metrics_handler.push_job_metrics(
        job_name=job_name,
        success=success,
        duration=duration,
        records=records,
        error_message=error_message
    )
```

### 3. **Stockage dans Pushgateway**

Les métriques sont envoyées via HTTP POST :
```
POST http://pushgateway:9091/metrics/job/cron_jobs/job_name/export_transactions_PEA

cron_job_success{job="cron_jobs",job_name="export_transactions_PEA"} 1
cron_job_duration_seconds{job="cron_jobs",job_name="export_transactions_PEA"} 0.014
cron_job_records_processed{job="cron_jobs",job_name="export_transactions_PEA"} 23
cron_job_last_execution_timestamp{job="cron_jobs",job_name="export_transactions_PEA"} 1730736000
```

### 4. **Scraping par Prometheus** (toutes les 15s)

Prometheus scrape le Pushgateway et stocke les time series :
```
cron_job_success{instance="",job="cron_jobs",job_name="export_transactions_PEA"} 1 @1730736000
```

### 5. **Évaluation des règles** (toutes les minutes)

Prometheus évalue les conditions PromQL :
```yaml
# Alerte CronJobFailed
expr: cron_job_success == 0
# Résultat : Vide (aucun job en échec) → Alerte inactive

# Alerte CronJobTooSlow
expr: cron_job_duration_seconds > 60
# Résultat : Vide (0.014s < 60s) → Alerte inactive
```

Si une condition est vraie pendant le délai `for`, l'alerte passe en état `pending` puis `firing`.

### 6. **Envoi vers Alertmanager** (si alerte active)

Si une alerte se déclenche :
```json
{
  "alertname": "CronJobFailed",
  "job_name": "export_transactions_PEA",
  "severity": "critical",
  "status": "firing"
}
```

Alertmanager applique :
- **Grouping** : Regroupe avec d'autres alertes similaires
- **Routing** : Envoie vers `critical-alerts` receiver
- **Notification** : Webhook ou email

### 7. **Visualisation dans Grafana**

Grafana interroge Prometheus en PromQL :
```promql
# Pour le panneau "Last Job Status"
cron_job_success

# Pour le tableau
max by (job_name) (cron_job_success)
max by (job_name) (cron_job_duration_seconds)
```

Et affiche les résultats dans les panneaux.

---

## 🧪 Tester le système

### Test 1 : Vérifier la configuration

```bash
# Vérifier que Prometheus charge les règles
curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool | grep -c '"name"'
# Doit afficher : 8 (nombre d'alertes)

# Vérifier les métriques dans Pushgateway
curl -s http://localhost:9091/metrics | grep cron_job_success

# Vérifier que Prometheus scrape
curl -s http://localhost:9090/api/v1/targets | grep pushgateway
```

### Test 2 : Simuler une alerte

```bash
# Simuler un job en échec
docker compose exec web python /app/test_alert_simulation.py failed

# Attendre 2 minutes (délai de l'alerte CronJobFailed)

# Vérifier l'alerte dans Prometheus
curl -s http://localhost:9090/api/v1/alerts | grep -i firing

# Vérifier dans Alertmanager
curl -s http://localhost:9093/api/v1/alerts
```

### Test 3 : Exécuter un vrai job

```bash
# Exécuter tous les 8 jobs
./test_all_jobs.sh

# Vérifier le dashboard
firefox http://localhost:3000

# Vérifier les métriques
curl -s http://localhost:9091/metrics | grep -c "cron_job_success"
# Doit afficher : 8 (8 jobs)
```

---

## 📊 Requêtes PromQL utiles

```promql
# Tous les jobs et leur statut
cron_job_success

# Jobs en échec
cron_job_success == 0

# Taux de succès sur 24h par job
avg_over_time(cron_job_success[24h])

# Durée moyenne par job
avg(cron_job_duration_seconds) by (job_name)

# Total des enregistrements traités aujourd'hui
sum(increase(cron_job_records_processed[1d])) by (job_name)

# Jobs qui n'ont pas tourné depuis 1h
(time() - cron_job_last_execution_timestamp) > 3600

# Top 3 des jobs les plus lents
topk(3, max(cron_job_duration_seconds) by (job_name))

# Nombre d'échecs dans les dernières 24h
count_over_time((cron_job_success == 0)[24h])
```

---

## 🔧 Configuration avancée

### Activer les notifications email

Éditer `alertmanager/config.yml` :

```yaml
receivers:
  - name: 'critical-alerts'
    email_configs:
      - to: 'admin@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@gmail.com'
        auth_password: 'your-app-password'  # App password Gmail
        headers:
          Subject: '🔴 ALERTE: {{ .GroupLabels.alertname }}'
        text: |
          Alerte: {{ .GroupLabels.alertname }}
          Job: {{ .CommonLabels.job_name }}
          Sévérité: {{ .CommonLabels.severity }}
          
          {{ range .Alerts }}
          - {{ .Annotations.summary }}
          {{ end }}
```

Puis redémarrer :
```bash
docker compose restart alertmanager
```

### Ajouter une nouvelle alerte

1. Éditer `prometheus/alerts.yml` :
```yaml
- alert: CronJobVeryFast
  expr: cron_job_duration_seconds < 0.001
  for: 1m
  labels:
    severity: info
  annotations:
    summary: "Job {{ $labels.job_name }} très rapide"
    description: "Durée : {{ $value }}s"
```

2. Redémarrer Prometheus :
```bash
docker compose restart prometheus
```

3. Vérifier :
```bash
curl http://localhost:9090/rules
```

### Modifier les seuils

Dans `prometheus/alerts.yml`, changer les valeurs :

```yaml
# Job lent : de 60s à 120s
- alert: CronJobTooSlow
  expr: cron_job_duration_seconds > 120  # ← Modifier ici
  for: 1m
```

---

## 📚 Documentation

- **MONITORING_CRON.md** : Architecture détaillée du monitoring
- **ALERTES_PROMETHEUS.md** : Guide complet des alertes
- **INSTALLATION.md** : Guide d'installation pas à pas
- **README.md** : Documentation générale du projet

---

## ✅ Checklist de vérification

- [ ] 8 jobs cron instrumentés dans `manage.py`
- [ ] Métriques visibles dans Pushgateway (`:9091`)
- [ ] Prometheus scrape le Pushgateway (`:9090/targets`)
- [ ] 8 règles d'alertes chargées (`:9090/rules`)
- [ ] Dashboard Grafana importé et fonctionnel (`:3000`)
- [ ] Alertmanager accessible (`:9093`)
- [ ] Test de simulation d'alerte réussi
- [ ] Jobs réels s'exécutent et poussent les métriques

---

**🎉 Le système de monitoring et d'alertes est maintenant complet et documenté !**
