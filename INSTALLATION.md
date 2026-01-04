# 📦 Installation du Monitoring Cron Jobs

## Prérequis

✅ Docker et Docker Compose V2 installés  
✅ Application Flask fonctionnelle  
✅ Services Prometheus, Grafana, Pushgateway actifs  

## 🚀 Étapes d'installation

### 1. Rebuild de l'image Docker

```bash
cd /home/shaky/projets/FlaskFolio-gestion-de-portefeuilles
docker compose down
docker compose build
docker compose up -d
```

### 2. Vérifier que tous les services sont actifs

```bash
docker compose ps
```

Vous devez voir :
- ✅ web (Flask)
- ✅ prometheus
- ✅ grafana
- ✅ pushgateway
- ✅ alertmanager
- ✅ cadvisor
- ✅ node-exporter

### 3. Test du monitoring

Exécutez le script de test :

```bash
./test_monitoring.sh
```

Le script va :
1. ✅ Vérifier que Pushgateway est accessible
2. ✅ Exécuter un job de test
3. ✅ Vérifier que les métriques sont poussées
4. ✅ Vérifier que Prometheus scrape le Pushgateway
5. ✅ Tester une requête PromQL

### 4. Import du dashboard Grafana

#### Option A : Via l'interface web

1. Aller sur http://localhost:3000
2. Se connecter (admin/admin par défaut)
3. Menu "Dashboards" → "Import"
4. Cliquer sur "Upload JSON file"
5. Sélectionner `grafana-dashboard-cron-jobs.json`
6. Choisir la datasource "Prometheus"
7. Cliquer sur "Import"

#### Option B : Via l'API

```bash
# Créer un token API dans Grafana d'abord, puis :
curl -X POST \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d @grafana-dashboard-cron-jobs.json \
  http://localhost:3000/api/dashboards/db
```

### 5. Accéder au dashboard

1. Ouvrir http://localhost:3000
2. Naviguer vers "Dashboards" → "Cron Jobs Monitoring"
3. Vous devriez voir :
   - 📊 Taux de succès des jobs (24h)
   - 📋 Statut de la dernière exécution
   - ⏱️ Durée d'exécution des jobs
   - 📈 Nombre d'enregistrements traités
   - 🕒 Timeline des exécutions

## 🧪 Test manuel des métriques

### Exécuter un job manuellement

```bash
docker compose exec web python manage.py export_all_stock_history_csv
```

### Vérifier les métriques dans Pushgateway

```bash
curl http://localhost:9091/metrics | grep cron_job
```

Vous devriez voir :
```
cron_job_success{instance="",job="export_all_stock_history_csv"} 1
cron_job_duration_seconds{instance="",job="export_all_stock_history_csv"} 0.523
cron_job_records_processed{instance="",job="export_all_stock_history_csv"} 1234
cron_job_last_execution_timestamp{instance="",job="export_all_stock_history_csv"} 1706522345
```

### Vérifier dans Prometheus

Ouvrir http://localhost:9090 et tester ces requêtes :

```promql
# Taux de succès
rate(cron_job_success[5m])

# Durée moyenne
avg(cron_job_duration_seconds) by (job)

# Dernières exécutions
cron_job_last_execution_timestamp

# Jobs en échec
cron_job_error
```

## 🔧 Troubleshooting

### Les métriques n'apparaissent pas dans Pushgateway

```bash
# Vérifier les logs de l'application
docker compose logs web | tail -50

# Vérifier que prometheus-client est installé
docker compose exec web pip list | grep prometheus-client
```

### Prometheus ne scrape pas le Pushgateway

```bash
# Vérifier la configuration
docker compose exec prometheus cat /etc/prometheus/prometheus.yml | grep pushgateway

# Vérifier les targets
curl http://localhost:9090/api/v1/targets | grep pushgateway
```

### Le dashboard Grafana est vide

1. Vérifier la datasource Prometheus :
   - Menu "Configuration" → "Data sources"
   - URL devrait être `http://prometheus:9090`
   - Cliquer sur "Save & test"

2. Vérifier que des métriques existent :
   ```bash
   curl -s 'http://localhost:9090/api/v1/query?query=cron_job_success' | python3 -m json.tool
   ```

3. Rafraîchir le dashboard et ajuster le Time Range

## 📅 Test des jobs cron programmés

Les jobs cron s'exécutent automatiquement :
- **Samedi à 8h00** : 8 exports
- **1er du mois à 9h00** : 4 exports

Pour voir les prochaines exécutions :

```bash
docker compose exec web crontab -l
```

Pour voir les logs d'exécution :

```bash
# Logs cron
docker compose exec web cat /app/logs_local/cron.log

# Logs manage.py
docker compose exec web cat /app/logs_local/manage.log
```

## 🎯 Prochaines étapes

1. **Configurer les alertes** (voir `MONITORING_CRON.md` section "Alertes Prometheus")
2. **Instrumenter les autres commandes** :
   - `export_transactions_csv` (déjà fait ✅)
   - `export_all_stock_history_csv` (déjà fait ✅)
   - `export_cash_mouvements_csv`
   - `export_portfolio_csv`
   - `export_all_stocks_csv`
3. **Personnaliser le dashboard** selon vos besoins
4. **Configurer les notifications** Alertmanager (email, Slack, etc.)

## 📚 Documentation complète

Voir `MONITORING_CRON.md` pour :
- Architecture détaillée
- Liste complète des métriques
- Requêtes PromQL avancées
- Configuration des alertes
- Guide de troubleshooting complet

## ✅ Validation

Une fois l'installation terminée, vous devriez avoir :

- ✅ Pushgateway accessible sur http://localhost:9091
- ✅ Prometheus scrape le Pushgateway (vérifiable sur http://localhost:9090/targets)
- ✅ Dashboard Grafana fonctionnel sur http://localhost:3000
- ✅ Métriques visibles après exécution d'un job
- ✅ Jobs cron programmés et fonctionnels
- ✅ Logs cron dans `/app/logs_local/cron.log`

---

**🎉 Félicitations ! Le monitoring de vos jobs cron est maintenant opérationnel !**
