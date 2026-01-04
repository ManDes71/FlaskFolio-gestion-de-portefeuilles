# 🔄 Articulation des fichiers de monitoring

## 📚 Fichiers impliqués

1. **prometheus/prometheus.yml** → Configuration Prometheus (scraping + alerting)
2. **prometheus/alerts.yml** → Règles d'alertes (conditions + seuils)
3. **alertmanager/config.yml** → Routage des alertes (notifications)
4. **pea_trading/utils/metrics.py** → Push des métriques vers Pushgateway
5. **Pushgateway** → Stockage temporaire des métriques

---

## 🔄 Flux général

```
┌─────────────────────────────────────────────────────────────────┐
│  1. APPLICATION FLASK (pea_trading/utils/metrics.py)            │
│     → Push métriques vers Pushgateway                           │
│     metrics_handler.push_scraping_metrics(success=1, ...)       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. PUSHGATEWAY :9091                                            │
│     → Stocke les métriques des jobs batch                       │
│     scraping_success{job="scraping_intraday"} = 1               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼ scrape_interval: 15s
┌─────────────────────────────────────────────────────────────────┐
│  3. PROMETHEUS :9090 (prometheus.yml)                            │
│     → Scrape Pushgateway toutes les 15s                         │
│     → Évalue les règles d'alertes toutes les 1m                 │
│     → Stocke les métriques (TSDB, rétention 15j)                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼ evaluation_interval: 1m
┌─────────────────────────────────────────────────────────────────┐
│  4. PROMETHEUS - RÈGLES (alerts.yml)                             │
│     → Évalue: scraping_success == 0 for 5m ?                    │
│     → État: inactive → pending → firing                         │
│     → Labels: severity, component, etc.                         │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼ Si alerte FIRING
┌─────────────────────────────────────────────────────────────────┐
│  5. ALERTMANAGER :9093 (config.yml)                              │
│     → Reçoit les alertes de Prometheus                          │
│     → Route selon severity (critical/warning)                   │
│     → Groupe et déduplique les alertes                          │
│     → Envoie aux receivers (email, webhook, etc.)               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📖 CAS 1 : Scraping échoue (ScrapingIntradayFailed)

### Timeline complète

#### T0 : 10:00:00 - APPLICATION FLASK

**📱 Job scraping_intraday s'exécute**

```python
# pea_trading/services/scheduler_jobs.py
def job_scraping_intraday():
    start_time = time.time()
    try:
        stats = scrape_boursorama_stocks(intraday=True)
        # ... traitement ...
    except Exception as e:
        # EXCEPTION : Connexion timeout à Boursorama
        metrics_handler.push_scraping_metrics(
            success=False,
            error=str(e)  # "Connection timeout"
        )
```

**Résultat** : Métriques d'échec poussées vers Pushgateway

---

#### T0 : 10:00:01 - PUSHGATEWAY

**🗄️ Métriques stockées**

```
scraping_success{job="scraping_intraday",job_type="scraping"} = 0
scraping_error_message{...} = "Connection timeout"
```

Accessible via :
```bash
curl http://localhost:9091/metrics | grep scraping_success
```

---

#### T0 : 10:00:15 - PROMETHEUS.YML (scrape_configs)

**📊 Configuration de scraping**

```yaml
# prometheus/prometheus.yml
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['pushgateway:9091']
```

**Action** : Prometheus scrape Pushgateway  
**Résultat** : `scraping_success = 0` stocké dans TSDB Prometheus

---

#### T0 : 10:01:00 - PROMETHEUS.YML (evaluation_interval)

**⏱️ Évaluation des règles**

```yaml
# prometheus/prometheus.yml
global:
  evaluation_interval: 1m
```

**Action** : Prometheus évalue **toutes** les règles dans `alerts.yml`  
**Fréquence** : Toutes les 1 minute

---

#### T0 : 10:01:00 - ALERTS.YML (règle ScrapingIntradayFailed)

**🚨 Première évaluation de la règle**

```yaml
# prometheus/alerts.yml
- alert: ScrapingIntradayFailed
  expr: scraping_success{job="scraping_intraday"} == 0
  for: 5m
  labels:
    severity: critical
    component: scraping
  annotations:
    summary: "Échec du scraping Boursorama"
    description: "Le scraping intraday a échoué..."
```

**Évaluation** : `scraping_success == 0` ? **OUI**  
**État** : `INACTIVE` → `PENDING`  
**Raison** : Condition vraie **MAIS** `for: 5m` non atteint

---

#### T0 : 10:02:00 à 10:05:00 - Évaluations suivantes

**⏱️ Prometheus continue d'évaluer toutes les minutes**

- 10:02:00 → `PENDING` (depuis 1 minute)
- 10:03:00 → `PENDING` (depuis 2 minutes)
- 10:04:00 → `PENDING` (depuis 3 minutes)
- 10:05:00 → `PENDING` (depuis 4 minutes)

**État** : Condition toujours vraie mais durée `for: 5m` pas encore atteinte

---

#### T0 : 10:06:00 - ALERTE DÉCLENCHE !

**🔥 Transition PENDING → FIRING**

**État** : `PENDING` → `FIRING`  
**Raison** : Condition vraie depuis **5 minutes**

**Alerte générée** :
```json
{
  "alertname": "ScrapingIntradayFailed",
  "severity": "critical",
  "component": "scraping",
  "summary": "Échec du scraping Boursorama",
  "description": "Le scraping intraday a échoué depuis 5 minutes",
  "value": "0"
}
```

---

#### T0 : 10:06:01 - PROMETHEUS.YML (alerting.alertmanagers)

**📬 Envoi de l'alerte à Alertmanager**

```yaml
# prometheus/prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

**Action** : Prometheus envoie l'alerte à `alertmanager:9093`

---

#### T0 : 10:06:02 - ALERTMANAGER CONFIG.YML (route)

**🔔 Routage de l'alerte**

```yaml
# alertmanager/config.yml
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'severity', 'component']
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 0s         # ← IMMÉDIAT pour critical
      repeat_interval: 1h
```

**Actions** :
1. ✅ Alerte correspond à `severity: critical`
2. ✅ Router vers receiver `'critical-alerts'`
3. ✅ Grouper par `[alertname, severity, component]`
4. ✅ Envoyer **immédiatement** (`group_wait: 0s`)

---

#### T0 : 10:06:02 - ALERTMANAGER CONFIG.YML (receivers)

**📧 Envoi de la notification**

```yaml
# alertmanager/config.yml
receivers:
  - name: 'critical-alerts'
    webhook_configs:
      - url: 'http://webhook.site/...'
        send_resolved: true
    # email_configs:  (si configuré)
    #   - to: 'admin@example.com'
    #     from: 'alertmanager@example.com'
    #     smarthost: 'smtp.gmail.com:587'
```

**Action** : Envoyer notification via webhook (ou email si configuré)

---

### 🎯 Résultat final

✅ Alerte visible dans Prometheus UI : http://localhost:9090/alerts  
✅ Alerte visible dans Alertmanager : http://localhost:9093/#/alerts  
✅ Notification envoyée (webhook/email selon config)  
✅ Dashboard Grafana affiche statut **FAILED** en rouge

---

## 📖 CAS 2 : Job cron trop lent (CronJobTooSlow)

### Timeline complète

#### T0 : 14:30:00 - APPLICATION FLASK

**📱 Job cron "export_all_stock_history" démarre**

```python
# Dans le job cron
start_time = time.time()

# ... traitement long (15000 records) ...

duration = time.time() - start_time  # = 125 secondes

metrics_handler.push_cron_metrics(
    job_name="export_all_stock_history",
    success=True,
    duration=125.5,
    records_processed=15000
)
```

**Résultat** : Job réussi mais **très lent** (125.5s)

---

#### T0 : 14:32:05 - PUSHGATEWAY

**🗄️ Métriques stockées**

```
cron_job_success{job_name="export_all_stock_history"} = 1
cron_job_duration_seconds{job_name="export_all_stock_history"} = 125.5
cron_job_records_processed{job_name="export_all_stock_history"} = 15000
```

---

#### T0 : 14:32:15 - PROMETHEUS scrape

**📊 Prometheus récupère les métriques**

**Action** : `cron_job_duration_seconds = 125.5` stocké dans TSDB

---

#### T0 : 14:33:00 - PROMETHEUS évalue les règles

**⏱️ Première évaluation après le job**

---

#### T0 : 14:33:00 - ALERTS.YML - Règle 1 (générique)

**🚨 CronJobTooSlow (règle générique pour tous les jobs)**

```yaml
# prometheus/alerts.yml
- alert: CronJobTooSlow
  expr: cron_job_duration_seconds > 60
  for: 1m
  labels:
    severity: warning
    component: cron
  annotations:
    summary: "Job cron {{ $labels.job_name }} est trop lent"
    description: "Durée: {{ $value }}s (seuil: 60s)"
```

**Évaluation** : `125.5 > 60` ? **OUI**  
**État** : `INACTIVE` → `PENDING`  
**Raison** : Condition vraie mais `for: 1m` non atteint

---

#### T0 : 14:33:00 - ALERTS.YML - Règle 2 (spécifique)

**🚨 CronJobHistoryTooSlow (règle spécifique pour export_all_stock_history)**

```yaml
# prometheus/alerts.yml
- alert: CronJobHistoryTooSlow
  expr: |
    cron_job_duration_seconds{
      job_name="export_all_stock_history"
    } > 120
  for: 1m
  labels:
    severity: warning
    component: cron
  annotations:
    summary: "Export historique trop lent"
    description: "Durée: {{ $value }}s (seuil: 120s)"
```

**Évaluation** : `125.5 > 120` ? **OUI**  
**État** : `INACTIVE` → `PENDING`

⚠️ **DEUX ALERTES** déclenchées simultanément !

---

#### T0 : 14:34:00 - 2ème évaluation (1 minute après)

**🔥 Les deux alertes passent FIRING**

**CronJobTooSlow** :
- Condition : `125.5 > 60` ? **OUI** (toujours car métrique persiste)
- `for: 1m` **ATTEINT** → `FIRING` !

**CronJobHistoryTooSlow** :
- Condition : `125.5 > 120` ? **OUI**
- `for: 1m` **ATTEINT** → `FIRING` !

---

#### T0 : 14:34:01 - PROMETHEUS envoie à Alertmanager

**📬 DEUX alertes envoyées simultanément**

**Alerte 1** :
```json
{
  "alertname": "CronJobTooSlow",
  "severity": "warning",
  "component": "cron",
  "job_name": "export_all_stock_history",
  "summary": "Job cron export_all_stock_history est trop lent"
}
```

**Alerte 2** :
```json
{
  "alertname": "CronJobHistoryTooSlow",
  "severity": "warning",
  "component": "cron",
  "job_name": "export_all_stock_history",
  "summary": "Export historique trop lent"
}
```

---

#### T0 : 14:34:02 - ALERTMANAGER route

**🔔 Routage des alertes warning**

```yaml
# alertmanager/config.yml
route:
  group_by: ['alertname', 'severity', 'component']
  routes:
    - match:
        severity: warning
      receiver: 'warning-alerts'
      group_wait: 30s        # ← ATTENTE 30s pour regrouper
      group_interval: 5m
      repeat_interval: 4h
```

**Actions** :
1. ✅ Les 2 alertes correspondent à `severity: warning`
2. ✅ Router vers receiver `'warning-alerts'`
3. ✅ Grouper par `[alertname, severity, component]`
4. ✅ **Attendre 30s** pour regrouper d'autres alertes similaires

---

#### T0 : 14:34:32 - ALERTMANAGER envoie (30s après)

**📧 Envoi d'UNE notification groupée**

```yaml
# alertmanager/config.yml
receivers:
  - name: 'warning-alerts'
    webhook_configs:
      - url: 'http://webhook.site/...'
```

**Action** : Envoyer **1 notification** groupée avec les 2 alertes

**Notification groupée** :
```json
[
  {"alertname": "CronJobTooSlow", "job_name": "export_all_stock_history", ...},
  {"alertname": "CronJobHistoryTooSlow", "job_name": "export_all_stock_history", ...}
]
```

---

### 🎯 Points clés de ce cas

✅ **DEUX alertes** déclenchées car DEUX règles matchent  
✅ `group_by` permet de regrouper les alertes similaires  
✅ `group_wait: 30s` évite d'envoyer une notification par alerte  
✅ `severity: warning` a un traitement différent de `critical`  
✅ `repeat_interval: 4h` évite de spammer si le problème persiste

---

## 🔑 Paramètres importants

### prometheus.yml

```yaml
global:
  scrape_interval: 15s      # Fréquence de récupération des métriques
  evaluation_interval: 1m   # Fréquence d'évaluation des règles

rule_files:
  - /etc/prometheus/alerts.yml  # Fichier des règles d'alertes

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']  # Où envoyer les alertes

scrape_configs:
  - job_name: 'pushgateway'
    static_configs:
      - targets: ['pushgateway:9091']  # Où récupérer les métriques
```

**Rôles** :
- `scrape_interval` : Délai max avant de voir une nouvelle métrique
- `evaluation_interval` : Délai entre évaluations des règles d'alertes
- `rule_files` : Fichiers contenant les règles d'alertes
- `alerting.alertmanagers` : Où envoyer les alertes déclenchées
- `scrape_configs` : Où récupérer les métriques

---

### alerts.yml

```yaml
groups:
  - name: scraping_alerts
    interval: 1m           # Surcharge evaluation_interval (optionnel)
    rules:
      - alert: ScrapingIntradayFailed
        expr: scraping_success == 0    # Condition PromQL
        for: 5m            # Durée avant FIRING
        labels:
          severity: critical   # Utilisé pour le routing dans Alertmanager
          component: scraping
        annotations:
          summary: "..."     # Message court
          description: "..." # Message détaillé avec variables {{ $value }}
```

**Rôles** :
- `expr` : Requête PromQL définissant la condition d'alerte
- `for` : Durée pendant laquelle la condition doit être vraie avant FIRING
- `labels` : Métadonnées utilisées pour le routing (severity, component, etc.)
- `annotations` : Messages affichés dans les notifications

**États des alertes** :
1. `INACTIVE` : Condition fausse
2. `PENDING` : Condition vraie mais durée `for` non atteinte
3. `FIRING` : Condition vraie depuis la durée `for`

---

### alertmanager/config.yml

```yaml
route:
  receiver: 'default-receiver'  # Receiver par défaut
  group_by: ['alertname', 'severity']  # Clés de regroupement
  group_wait: 10s       # Attente avant envoi du 1er groupe
  group_interval: 5m    # Délai entre envois d'un même groupe
  repeat_interval: 4h   # Délai entre re-notifications

  routes:               # Routes spécifiques
    - match:
        severity: critical
      receiver: 'critical-alerts'
      group_wait: 0s    # Immédiat pour critical

inhibit_rules:          # Éviter les doublons
  - source_match:
      alertname: 'AllJobsFailed'
    target_match:
      alertname: 'JobFailed'

receivers:              # Destinations finales
  - name: 'critical-alerts'
    webhook_configs:
      - url: 'http://...'
    email_configs:
      - to: 'admin@example.com'
```

**Rôles** :
- `route` : Définit comment router et grouper les alertes
- `group_by` : Clés pour regrouper les alertes similaires
- `group_wait` : Temps d'attente pour regrouper les alertes
- `group_interval` : Intervalle entre envois de groupes d'alertes
- `repeat_interval` : Fréquence de re-notification si alerte persiste
- `inhibit_rules` : Supprime les alertes redondantes
- `receivers` : Définit où et comment envoyer les notifications

---

## 📝 Résumé

### Workflow complet

1. **Application** → Push métriques → **Pushgateway**
2. **Prometheus** → Scrape Pushgateway (`scrape_interval`)
3. **Prometheus** → Évalue règles `alerts.yml` (`evaluation_interval`)
4. **Alerte PENDING** si condition vraie
5. **Alerte FIRING** si condition vraie pendant durée `for`
6. **Prometheus** → Envoie à **Alertmanager**
7. **Alertmanager** → Route selon `severity` (`config.yml`)
8. **Alertmanager** → Groupe les alertes (`group_by`, `group_wait`)
9. **Alertmanager** → Envoie aux `receivers` (webhook, email, etc.)

---

### Timing important

| Paramètre | Valeur | Impact |
|-----------|--------|--------|
| `scrape_interval` | 15s | Délai max avant voir nouvelle métrique |
| `evaluation_interval` | 1m | Délai entre évaluations de règles |
| `for` | 5m | Durée avant déclencher l'alerte |
| `group_wait` (critical) | 0s | Envoi immédiat pour alertes critiques |
| `group_wait` (warning) | 30s | Attente pour regrouper alertes warning |
| `repeat_interval` | 4h | Fréquence des re-notifications |

---

### Exemple de délai total (Cas 1)

| Temps | Événement |
|-------|-----------|
| T0 | Métrique poussée vers Pushgateway |
| T0 + 15s | Prometheus scrape |
| T0 + 1m | Prometheus évalue (alerte → PENDING) |
| T0 + 6m | Alerte → FIRING (`for: 5m` atteint) |
| T0 + 6m | Alertmanager reçoit l'alerte |
| T0 + 6m | Envoi immédiat (critical, `group_wait: 0s`) |

**Délai total** : ~6 minutes entre l'échec et la notification

---

## 🎓 Points clés à retenir

1. **prometheus.yml** = Configuration globale (scraping + alerting)
2. **alerts.yml** = Définition des règles et conditions
3. **config.yml** (Alertmanager) = Routage et notifications
4. **Trois états d'alerte** : INACTIVE → PENDING → FIRING
5. **group_by** évite les notifications en double
6. **severity** permet un traitement différencié (critical vs warning)
7. **for** évite les faux positifs (alerte transitoire)
8. **repeat_interval** évite le spam de notifications
