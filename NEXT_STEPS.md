# 🚀 Prochaines étapes - Monitoring Cron Jobs

## ✅ Ce qui est fait

- ✅ Infrastructure Pushgateway opérationnelle
- ✅ Module `pea_trading/utils/metrics.py` créé
- ✅ 2 commandes instrumentées :
  - `export_transactions_csv`
  - `export_all_stock_history_csv`
- ✅ Dashboard Grafana fonctionnel
- ✅ Documentation complète (`MONITORING_CRON.md`)

## 📋 Commandes à instrumenter

### Commandes d'export à monitorer

```bash
# Voir toutes les commandes disponibles
docker compose exec web python manage.py --help
```

Commandes prioritaires à instrumenter :

1. **export_cash_mouvements_csv**
2. **export_portfolio_csv**  
3. **export_all_stocks_csv**

### 🔧 Pattern d'instrumentation

Pour chaque commande, ajouter ce pattern :

```python
@manager.command
def ma_commande():
    """Description de la commande"""
    
    # === DÉBUT INSTRUMENTATION ===
    import time
    from pea_trading.utils.metrics import metrics_handler
    
    start_time = time.time()
    success = False
    records = 0
    error_message = None
    job_name = "ma_commande"  # Nom unique du job
    
    logger.info(f"📤 Commande '{job_name}' exécutée")
    # === FIN INITIALISATION ===
    
    with app.app_context():
        try:
            # === LOGIQUE MÉTIER ICI ===
            result = faire_le_travail()
            
            # === COMPTER LES ENREGISTREMENTS ===
            records = compter_les_enregistrements()
            # Exemples :
            # - records = len(portfolio.transactions)
            # - records = StockPriceHistory.query.count()
            # - records = len(data_exportees)
            
            success = True
            logger.info(f"✅ {job_name} terminé avec succès ({records} enregistrements)")
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Erreur {job_name}: {e}")
            print(f"❌ Erreur : {e}")
            
        finally:
            # === POUSSER LES MÉTRIQUES ===
            duration = time.time() - start_time
            metrics_handler.push_job_metrics(
                job_name=job_name,
                success=success,
                duration=duration,
                records=records,
                error_message=error_message
            )
```

## 📊 Dashboard Grafana

### Mise à jour du dashboard

Le dashboard a été optimisé avec :

1. **Panneau "Last Job Status"** : Affiche le statut actuel (✅/❌)
2. **Tableau optimisé** : Une ligne par job avec fusion correcte des métriques
3. **Timestamp corrigé** : Multiplication par 1000 pour l'affichage

### Pour mettre à jour :

```bash
# 1. Copier le contenu du fichier JSON
cat grafana/provisioning/dashboards/grafana-dashboard-cron-jobs.json

# 2. Dans Grafana :
#    - Dashboard settings (⚙️)
#    - JSON Model
#    - Coller le contenu
#    - Save changes → Save dashboard
```

## 🔔 Configurer les alertes (optionnel)

### Créer des alertes Prometheus

Créer le fichier `prometheus/alerts.yml` :

```yaml
groups:
  - name: cron_jobs
    interval: 1m
    rules:
      # Alerte si un job échoue
      - alert: CronJobFailed
        expr: cron_job_success == 0
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Job cron {{ $labels.job_name }} a échoué"
          description: "Le job {{ $labels.job_name }} est en échec depuis 2 minutes"
      
      # Alerte si un job est trop lent
      - alert: CronJobTooSlow
        expr: cron_job_duration_seconds > 60
        for: 1m
        labels:
          severity: info
        annotations:
          summary: "Job cron {{ $labels.job_name }} est lent"
          description: "Le job {{ $labels.job_name }} prend {{ $value }}s à s'exécuter"
      
      # Alerte si un job n'a pas été exécuté
      - alert: CronJobNotExecuted
        expr: (time() - cron_job_last_execution_timestamp) > 86400
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Job cron {{ $labels.job_name }} non exécuté"
          description: "Le job {{ $labels.job_name }} n'a pas été exécuté depuis plus de 24h"
```

### Ajouter au prometheus.yml

```yaml
rule_files:
  - /etc/prometheus/alerts.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

## 🧪 Tests

### Test manuel d'un job

```bash
# Exécuter un job
docker compose exec web python manage.py export_all_stock_history_csv

# Vérifier les métriques
curl -s http://localhost:9091/metrics | grep cron_job

# Vérifier dans Prometheus
# http://localhost:9090 → Query : cron_job_success

# Vérifier dans Grafana
# http://localhost:3000 → Dashboard "Cron Jobs Monitoring"
```

### Test automatisé

```bash
# Utiliser le script de test
./test_monitoring.sh
```

## 📈 Métriques disponibles

| Métrique | Description | Type |
|----------|-------------|------|
| `cron_job_success` | 1 = succès, 0 = échec | Gauge |
| `cron_job_duration_seconds` | Durée d'exécution en secondes | Gauge |
| `cron_job_records_processed` | Nombre d'enregistrements traités | Gauge |
| `cron_job_last_execution_timestamp` | Timestamp Unix de la dernière exécution | Gauge |
| `cron_job_error` | Message d'erreur (si échec) | Gauge |

## 🔍 Requêtes PromQL utiles

```promql
# Statut actuel de tous les jobs
cron_job_success

# Jobs en échec
cron_job_success == 0

# Durée moyenne par job
avg(cron_job_duration_seconds) by (job_name)

# Jobs non exécutés depuis 1h
(time() - cron_job_last_execution_timestamp) > 3600

# Taux de succès sur 24h
avg_over_time(cron_job_success[24h])
```

## 📚 Documentation

- **`MONITORING_CRON.md`** : Documentation technique complète
- **`INSTALLATION.md`** : Guide d'installation
- **`README.md`** : Commandes Docker utiles

## 🎯 Objectifs atteints

✅ **Visibilité** : Voir en temps réel l'état des jobs cron  
✅ **Traçabilité** : Historique des exécutions  
✅ **Debugging** : Métriques détaillées (durée, records, erreurs)  
✅ **Alerting** : Infrastructure prête pour les alertes  

---

**🚀 Le système de monitoring est opérationnel ! Il suffit maintenant d'instrumenter les autres commandes selon le besoin.**
