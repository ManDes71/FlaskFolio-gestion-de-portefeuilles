# 📊 Monitoring des Jobs Cron avec Prometheus & Grafana

## Architecture

```
Cron Job → Python manage.py → Métriques → Pushgateway → Prometheus → Grafana
```

## Métriques collectées

Chaque job cron pousse automatiquement les métriques suivantes vers le Pushgateway :

| Métrique | Description | Type | Labels |
|----------|-------------|------|--------|
| `cron_job_success` | Statut d'exécution (1=succès, 0=échec) | Gauge | `job_name` |
| `cron_job_duration_seconds` | Durée d'exécution en secondes | Gauge | `job_name` |
| `cron_job_records_processed` | Nombre d'enregistrements traités | Gauge | `job_name` |
| `cron_job_last_execution_timestamp` | Timestamp Unix de dernière exécution | Gauge | `job_name` |
| `cron_job_error` | Information d'erreur (si échec) | Gauge | `job_name`, `error_type` |

## Configuration

### 1. Vérifier que Pushgateway est actif

```bash
docker compose ps pushgateway
curl http://localhost:9091/metrics
```

### 2. Vérifier que Prometheus scrape le Pushgateway

Aller sur http://localhost:9090/targets et vérifier que la target `pushgateway` est UP.

### 3. Importer le dashboard Grafana

1. Aller sur http://localhost:3000
2. Dashboard → Import
3. Copier le contenu de `grafana-dashboard-cron-jobs.json`
4. Coller et cliquer sur "Load"

## Utilisation

### Tester manuellement

```bash
# Exécuter un job et voir les métriques poussées
docker compose exec web python manage.py export_all_stock_history_csv

# Vérifier les métriques dans le Pushgateway
curl http://localhost:9091/metrics | grep cron_job
```

### Ajouter le monitoring à une nouvelle commande

```python
@cli.command("ma_nouvelle_commande")
def ma_nouvelle_commande():
    start_time = time.time()
    success = False
    records = 0
    error_message = None
    job_name = "ma_nouvelle_commande"
    
    try:
        # Votre code ici
        records = 42  # Nombre d'enregistrements traités
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

## Requêtes Prometheus utiles

### Taux de succès sur 24h
```promql
avg_over_time(cron_job_success[24h])
```

### Durée moyenne par job
```promql
avg(cron_job_duration_seconds) by (job_name)
```

### Jobs en échec
```promql
cron_job_success == 0
```

### Temps depuis dernière exécution
```promql
time() - cron_job_last_execution_timestamp
```

## Alertes Prometheus recommandées

### Job en échec
```yaml
- alert: CronJobFailed
  expr: cron_job_success == 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Job cron {{ $labels.job_name }} en échec"
    description: "Le job {{ $labels.job_name }} a échoué"
```

### Job trop lent
```yaml
- alert: CronJobTooSlow
  expr: cron_job_duration_seconds > 300
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Job cron {{ $labels.job_name }} trop lent"
    description: "Le job {{ $labels.job_name }} a pris {{ $value }}s (> 5min)"
```

### Job non exécuté
```yaml
- alert: CronJobNotExecuted
  expr: time() - cron_job_last_execution_timestamp > 86400
  for: 1h
  labels:
    severity: critical
  annotations:
    summary: "Job cron {{ $labels.job_name }} non exécuté depuis 24h"
    description: "Le job {{ $labels.job_name }} n'a pas été exécuté depuis 24h"
```

## Dashboard Grafana

Le dashboard fourni contient :

### 📊 Panels principaux

1. **Job Success Rate (24h)** : Taux de succès global des jobs
2. **Last Execution Status** : Tableau avec état, durée, records et dernière exécution
3. **Job Execution Duration** : Graphique temporel de durée d'exécution
4. **Records Processed per Job** : Nombre d'enregistrements traités
5. **Job Execution Timeline** : Timeline visuelle succès/échec

### 🔔 Variables

- `$job` : Filtrer par nom de job
- `$interval` : Période d'agrégation

## Troubleshooting

### Les métriques ne s'affichent pas dans Grafana

1. Vérifier que le Pushgateway reçoit les métriques :
   ```bash
   curl http://localhost:9091/metrics | grep cron_job
   ```

2. Vérifier que Prometheus scrape le Pushgateway :
   ```bash
   curl http://localhost:9090/api/v1/targets | grep pushgateway
   ```

3. Tester une requête Prometheus :
   ```bash
   curl 'http://localhost:9090/api/v1/query?query=cron_job_success'
   ```

### Erreur "Connection refused" vers Pushgateway

Vérifier que le service est accessible depuis le conteneur web :
```bash
docker compose exec web curl http://pushgateway:9091/metrics
```

### Métriques obsolètes

Pour nettoyer les métriques du Pushgateway :
```bash
curl -X PUT http://localhost:9091/api/v1/admin/wipe
```

## Bonnes pratiques

1. ✅ Toujours inclure le `finally` pour pousser les métriques même en cas d'erreur
2. ✅ Utiliser des noms de jobs descriptifs et cohérents
3. ✅ Inclure le nombre d'enregistrements traités quand pertinent
4. ✅ Logger les erreurs avant de pousser les métriques
5. ✅ Monitorer régulièrement le dashboard pour détecter les anomalies
