# 🚨 Alertes Prometheus - Jobs Cron

## 📋 Alertes configurées

### 1. ❌ **CronJobFailed** - Job en échec (CRITIQUE)
- **Condition** : `cron_job_success == 0`
- **Délai** : 2 minutes
- **Sévérité** : `critical`
- **Description** : Alerte immédiate quand un job échoue

### 2. ⚠️ **CronJobTooSlow** - Job trop lent (WARNING)
- **Condition** : `cron_job_duration_seconds > 60`
- **Délai** : 1 minute
- **Sévérité** : `warning`
- **Description** : Job prend plus de 60 secondes

### 3. 🕐 **CronJobHistoryTooSlow** - Export historique lent (WARNING)
- **Condition** : `cron_job_duration_seconds{job_name="export_all_stock_history"} > 120`
- **Délai** : 1 minute
- **Sévérité** : `warning`
- **Description** : Export historique prend plus de 2 minutes

### 4. 📅 **CronJobNotExecutedFor8Days** - Job non exécuté 8j (WARNING)
- **Condition** : `(time() - cron_job_last_execution_timestamp) > 691200`
- **Délai** : 5 minutes
- **Sévérité** : `warning`
- **Description** : Job n'a pas tourné depuis 8 jours

### 5. 🔴 **CronJobNotExecutedFor2Weeks** - Job non exécuté 2 semaines (CRITIQUE)
- **Condition** : `(time() - cron_job_last_execution_timestamp) > 1209600`
- **Délai** : 5 minutes
- **Sévérité** : `critical`
- **Description** : Job n'a pas tourné depuis 2 semaines

### 6. 📊 **CronJobNoRecordsProcessed** - Aucun enregistrement (WARNING)
- **Condition** : `cron_job_success == 1 and cron_job_records_processed == 0`
- **Délai** : 5 minutes
- **Sévérité** : `warning`
- **Description** : Job réussit mais traite 0 enregistrement

### 7. 🔥 **AllCronJobsFailed** - Tous les jobs en échec (CRITIQUE)
- **Condition** : `count(cron_job_success == 0) >= 3`
- **Délai** : 5 minutes
- **Sévérité** : `critical`
- **Description** : 3 jobs ou plus en échec simultané

### 8. ⏱️ **CronJobStuckRunning** - Job bloqué (WARNING)
- **Condition** : `(time() - cron_job_last_execution_timestamp) < 60 and cron_job_duration_seconds > 300`
- **Délai** : 10 minutes
- **Sévérité** : `warning`
- **Description** : Job semble bloqué depuis plus de 5 minutes

---

## 🧪 Test des alertes

### 1. Vérifier que les alertes sont chargées

```bash
./test_alerts.sh
```

Ou manuellement :
```bash
curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool
```

### 2. Simuler un job en échec

```bash
docker compose exec web python -c "
from pea_trading.utils.metrics import metrics_handler
metrics_handler.push_job_metrics(
    job_name='test_job_failed',
    success=False,
    duration=1.5,
    records=0,
    error_message='Test simulation échec'
)
print('✅ Métrique d\'échec envoyée')
"
```

### 3. Simuler un job trop lent

```bash
docker compose exec web python -c "
from pea_trading.utils.metrics import metrics_handler
metrics_handler.push_job_metrics(
    job_name='test_job_slow',
    success=True,
    duration=90.0,
    records=100,
    error_message=None
)
print('✅ Métrique de job lent envoyée')
"
```

### 4. Vérifier les alertes actives

Attendre 2 minutes puis :

```bash
curl -s http://localhost:9090/api/v1/alerts | python3 -m json.tool | grep -A10 firing
```

Ou via l'interface web :
- **Prometheus Alerts** : http://localhost:9090/alerts
- **Prometheus Rules** : http://localhost:9090/rules
- **Alertmanager** : http://localhost:9093

---

## 📬 Configuration Alertmanager

Le fichier `alertmanager/config.yml` gère l'envoi des alertes.

### Receivers configurés :

1. **default-receiver** : Webhook vers localhost:5001/webhook
2. **critical-alerts** : Alertes critiques avec envoi immédiat
3. **warning-alerts** : Alertes warnings regroupées

### Configuration email (optionnel)

Décommenter et personnaliser dans `alertmanager/config.yml` :

```yaml
email_configs:
  - to: 'admin@example.com'
    from: 'alertmanager@example.com'
    smarthost: 'smtp.gmail.com:587'
    auth_username: 'your-email@gmail.com'
    auth_password: 'your-app-password'
    headers:
      Subject: '🔴 ALERTE CRITIQUE: {{ .GroupLabels.alertname }}'
```

### Inhibition rules

- Si `AllCronJobsFailed` se déclenche, supprime les alertes `CronJobFailed` individuelles
- Si `CronJobNotExecutedFor2Weeks` se déclenche, supprime `CronJobNotExecutedFor8Days`

---

## 🔍 Accès aux interfaces

| Service | URL | Description |
|---------|-----|-------------|
| **Prometheus Rules** | http://localhost:9090/rules | Liste des règles d'alertes |
| **Prometheus Alerts** | http://localhost:9090/alerts | Alertes actives et historique |
| **Alertmanager** | http://localhost:9093 | Gestion des notifications |
| **Grafana Dashboard** | http://localhost:3000 | Visualisation des métriques |
| **Pushgateway** | http://localhost:9091 | Métriques poussées |

---

## 🛠️ Troubleshooting

### Les alertes ne se déclenchent pas

1. Vérifier que Prometheus charge les règles :
   ```bash
   docker compose logs prometheus | grep -i "rule\|alert"
   ```

2. Vérifier les métriques dans le Pushgateway :
   ```bash
   curl -s http://localhost:9091/metrics | grep cron_job_success
   ```

3. Vérifier que Prometheus scrape le Pushgateway :
   ```bash
   curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool | grep pushgateway
   ```

### Alertmanager non accessible

```bash
# Vérifier l'état
docker compose ps alertmanager

# Voir les logs
docker compose logs alertmanager

# Redémarrer
docker compose restart alertmanager
```

### Modifier les seuils

Éditer `prometheus/alerts.yml` puis :

```bash
docker compose restart prometheus
```

---

## 📊 Exemples de requêtes PromQL

```promql
# Voir tous les jobs en échec
cron_job_success == 0

# Voir les jobs lents
cron_job_duration_seconds > 60

# Taux de succès par job
avg_over_time(cron_job_success[24h])

# Jobs non exécutés depuis 1h
(time() - cron_job_last_execution_timestamp) > 3600

# Nombre total d'enregistrements traités aujourd'hui
sum(increase(cron_job_records_processed[1d])) by (job_name)
```

---

## ✅ Validation

Pour valider que tout fonctionne :

```bash
# 1. Vérifier que les 8 alertes sont chargées
curl -s http://localhost:9090/api/v1/rules | grep -o '"name":' | wc -l
# Doit afficher: 8

# 2. Simuler un échec et vérifier l'alerte
docker compose exec web python -c "from pea_trading.utils.metrics import metrics_handler; metrics_handler.push_job_metrics('test', False, 1, 0, 'Test')"

# 3. Attendre 2 minutes et vérifier
curl -s http://localhost:9090/api/v1/alerts | grep -i firing

# 4. Consulter Alertmanager
firefox http://localhost:9093
```

---
### 🧪 Tester les alertes

```bash
# Simuler un job en échec
docker compose exec web python /app/test_alert_simulation.py failed

# Simuler un job lent
docker compose exec web python /app/test_alert_simulation.py slow

# Simuler un job vide
docker compose exec web python /app/test_alert_simulation.py empty

# Tout tester d'un coup
docker compose exec web python /app/test_alert_simulation.py all
```

Puis consulter : http://localhost:9090/alerts (attendre 1-2 minutes)


**✅ Les alertes Prometheus sont maintenant configurées et opérationnelles !**
