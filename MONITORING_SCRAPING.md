# 📊 Monitoring du Scraping Intraday Boursorama

## 📑 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Métriques collectées](#métriques-collectées)
4. [Alertes Prometheus](#alertes-prometheus)
5. [Dashboard Grafana](#dashboard-grafana)
6. [Guide d'utilisation](#guide-dutilisation)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## 🎯 Vue d'ensemble

Ce système de monitoring permet de surveiller en temps réel le scraping intraday des cours Boursorama. Il collecte 10 métriques, déclenche 5 alertes automatiques et affiche les données dans un dashboard Grafana interactif.

### Composants

- **Flask Application** : Exécute le scraping et pousse les métriques
- **Pushgateway** : Collecte et conserve les métriques des jobs batch
- **Prometheus** : Scrape les métriques et évalue les alertes
- **Alertmanager** : Gère les notifications d'alertes
- **Grafana** : Visualisation temps réel avec 6 panels

### Flux de données

```
┌─────────────────┐
│  Flask App      │
│  (Scraping)     │
└────────┬────────┘
         │ push metrics
         ▼
┌─────────────────┐
│  Pushgateway    │
│  :9091          │
└────────┬────────┘
         │ scrape (15s)
         ▼
┌─────────────────┐     ┌──────────────┐
│  Prometheus     │────▶│ Alertmanager │
│  :9090          │     │ :9093        │
└────────┬────────┘     └──────────────┘
         │ datasource
         ▼
┌─────────────────┐
│  Grafana        │
│  :3000          │
└─────────────────┘
```

---

## 🏗️ Architecture

### Code instrumenté

**Fichier** : `pea_trading/services/scheduler_jobs.py`

La fonction `job_scraping_intraday()` est entièrement instrumentée :

```python
def job_scraping_intraday():
    """Job schedulé pour scraping intraday avec monitoring complet"""
    start_time = time.time()
    
    # Compteurs
    total_scraped = 0
    matched_isins = 0
    updated = 0
    history_created = 0
    history_updated = 0
    
    try:
        # Exécution du scraping
        with current_app.app_context():
            stats = scrape_boursorama_stocks(intraday=True)
            # ... traitement ...
            
        # Push métriques de succès
        metrics_handler.push_scraping_metrics(
            success=True,
            duration=duration,
            stocks_scraped=total_scraped,
            # ... autres métriques ...
        )
        
    except Exception as e:
        # Push métriques d'échec
        metrics_handler.push_scraping_metrics(
            success=False,
            error=str(e)
        )
    finally:
        logger.info("✅ Scraping intraday terminé.")
```

### Métriques Handler

**Fichier** : `pea_trading/utils/metrics.py`

```python
def push_scraping_metrics(self, success, duration=None, stocks_scraped=0, 
                         stocks_matched=0, stocks_updated=0, 
                         history_created=0, history_updated=0, 
                         match_rate=0.0, error=""):
    """Pousse les métriques du scraping vers Pushgateway"""
    
    # Configuration des métriques
    registry = CollectorRegistry()
    
    # Gauges pour chaque métrique
    g_success = Gauge('scraping_success', '...', registry=registry)
    g_duration = Gauge('scraping_duration_seconds', '...', registry=registry)
    # ... autres métriques ...
    
    # Push avec grouping_key
    pushadd_to_gateway(
        gateway=f'{self.pushgateway_url}',
        job='scraping_intraday',
        registry=registry,
        grouping_key={'job_type': 'scraping'}
    )
```

**Note importante** : Utilisation de `pushadd_to_gateway` avec `grouping_key` pour éviter l'écrasement des métriques par d'autres jobs.

---

## 📈 Métriques collectées

### Liste des 10 métriques

| Métrique | Type | Description | Valeurs |
|----------|------|-------------|---------|
| `scraping_success` | Gauge | Statut d'exécution | 1=succès, 0=échec |
| `scraping_duration_seconds` | Gauge | Durée d'exécution | Secondes (float) |
| `scraping_stocks_scraped_total` | Gauge | Nombre total d'actions scrapées | ~189 stocks PEA |
| `scraping_stocks_matched_count` | Gauge | Nombre d'ISINs trouvés en BDD | 0-36 |
| `scraping_stocks_updated_count` | Gauge | Nombre de cours mis à jour | 0-36 |
| `scraping_history_created_count` | Gauge | Nouveaux enregistrements historique | 0-36 |
| `scraping_history_updated_count` | Gauge | Historiques mis à jour | 0-36 |
| `scraping_match_rate_percent` | Gauge | Taux de correspondance ISIN | % (float) |
| `scraping_last_execution_timestamp` | Gauge | Timestamp dernière exécution | Unix timestamp |
| `scraping_error_message` | Gauge | Message d'erreur si échec | String (label) |

### Valeurs typiques en production

**Scraping réussi** :
```
scraping_success = 1
scraping_duration_seconds = 54.45 - 68.22
scraping_stocks_scraped_total = 189
scraping_stocks_matched_count = 31
scraping_stocks_updated_count = 31
scraping_history_created_count = 0-1
scraping_history_updated_count = 30-31
scraping_match_rate_percent = 16.4
```

**Scraping échoué** :
```
scraping_success = 0
scraping_error_message = "Connection timeout to Boursorama"
```

### Consultation des métriques

**Pushgateway** (métriques brutes) :
```bash
curl http://localhost:9091/metrics | grep scraping_
```

**Prometheus** (avec requêtes PromQL) :
```bash
# Dernière valeur de succès
curl 'http://localhost:9090/api/v1/query?query=scraping_success'

# Durée moyenne sur 1h
curl 'http://localhost:9090/api/v1/query?query=avg_over_time(scraping_duration_seconds[1h])'

# Taux de match sur 24h
curl 'http://localhost:9090/api/v1/query?query=scraping_match_rate_percent'
```

---

## 🚨 Alertes Prometheus

### Configuration

**Fichier** : `prometheus/alerts.yml`

5 alertes configurées pour détecter les anomalies du scraping.

### 1. ScrapingIntradayFailed

**Condition** : Le scraping a échoué  
**Sévérité** : `critical`  
**Déclenchement** : `success == 0` pendant 5 minutes

```yaml
- alert: ScrapingIntradayFailed
  expr: scraping_success{job="scraping_intraday"} == 0
  for: 5m
  labels:
    severity: critical
    component: scraping
  annotations:
    summary: "Échec du scraping Boursorama"
    description: "Le scraping intraday a échoué (success=0) depuis 5 minutes"
```

**Actions recommandées** :
1. Vérifier les logs : `docker compose logs web | grep scraping`
2. Tester manuellement : `docker compose exec web python manage.py scrape_intraday`
3. Vérifier la connexion à Boursorama
4. Vérifier l'espace disque

### 2. ScrapingIntradayTooSlow

**Condition** : Le scraping prend trop de temps  
**Sévérité** : `warning`  
**Déclenchement** : `duration > 600s` (10 minutes) pendant 3 minutes

```yaml
- alert: ScrapingIntradayTooSlow
  expr: scraping_duration_seconds{job="scraping_intraday"} > 600
  for: 3m
  labels:
    severity: warning
    component: scraping
  annotations:
    summary: "Scraping intraday trop lent"
    description: "Durée: {{ $value }}s (seuil: 600s)"
```

**Causes possibles** :
- Connexion internet lente
- Boursorama répond lentement
- Ressources CPU/mémoire insuffisantes
- Trop d'ISINs en base de données

**Actions recommandées** :
1. Vérifier la bande passante réseau
2. Monitorer les ressources : `docker stats`
3. Optimiser les requêtes SQL si nécessaire

### 3. ScrapingMatchRateLow

**Condition** : Trop peu d'ISINs trouvés  
**Sévérité** : `warning`  
**Déclenchement** : `match_rate < 5%` pendant 15 minutes

```yaml
- alert: ScrapingMatchRateLow
  expr: scraping_match_rate_percent{job="scraping_intraday"} < 5
  for: 15m
  labels:
    severity: warning
    component: scraping
  annotations:
    summary: "Taux de correspondance ISIN très faible"
    description: "Taux: {{ $value }}% (seuil: 5%)"
```

**Causes possibles** :
- Structure HTML de Boursorama modifiée
- Base de données vide ou corrompue
- Problème de parsing des ISINs

**Actions recommandées** :
1. Vérifier le nombre d'ISINs en BDD : `python count_isins.py`
2. Vérifier les logs de parsing
3. Tester le scraper sur une page : `curl https://www.boursorama.com/bourse/actions/cotations/...`

### 4. ScrapingNoUpdates

**Condition** : Scraping réussi mais aucune mise à jour  
**Sévérité** : `warning`  
**Déclenchement** : `success==1 AND updated==0` pendant 30 minutes

```yaml
- alert: ScrapingNoUpdates
  expr: |
    scraping_success{job="scraping_intraday"} == 1
    and scraping_stocks_updated_count{job="scraping_intraday"} == 0
  for: 30m
  labels:
    severity: warning
    component: scraping
  annotations:
    summary: "Scraping sans mise à jour"
    description: "Aucun cours mis à jour depuis 30 minutes"
```

**Causes possibles** :
- Marchés fermés (hors horaires 9h-18h)
- Weekend ou jour férié
- Aucun ISIN ne correspond aux valeurs scrapées
- Prix identiques à ceux déjà en BDD

**Actions recommandées** :
1. Vérifier l'horaire : scraping prévu Lun-Ven 9h-18h
2. Vérifier `stocks_matched_count` : si 0, problème de matching
3. Vérifier les logs pour voir si des prix ont changé

### 5. ScrapingNotExecutedFor1Hour

**Condition** : Pas d'exécution depuis longtemps  
**Sévérité** : `critical`  
**Déclenchement** : `last_execution > 3600s` (1h) pendant 10 minutes

```yaml
- alert: ScrapingNotExecutedFor1Hour
  expr: |
    (time() - scraping_last_execution_timestamp{job="scraping_intraday"}) > 3600
  for: 10m
  labels:
    severity: critical
    component: scraping
  annotations:
    summary: "Scraping non exécuté depuis 1h"
    description: "Dernière exécution: {{ $value | humanizeDuration }}"
```

**Causes possibles** :
- APScheduler arrêté ou planté
- Application Flask plantée
- Container Docker arrêté

**Actions recommandées** :
1. Vérifier l'état des containers : `docker compose ps`
2. Vérifier les logs APScheduler : `docker compose logs web | grep scheduler`
3. Redémarrer l'application : `docker compose restart web`

### Consultation des alertes

**Prometheus UI** :
```
http://localhost:9090/alerts
```

**API Prometheus** :
```bash
# Toutes les alertes
curl http://localhost:9090/api/v1/alerts | jq

# Alertes scraping uniquement
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.component=="scraping")'
```

**Alertmanager UI** :
```
http://localhost:9093/#/alerts
```

---

## 📊 Dashboard Grafana

### Accès

**URL** : http://localhost:3000/d/scraping_intraday/

**Credentials par défaut** :
- Username : `admin`
- Password : `admin`

### Configuration

- **Refresh** : 30 secondes (automatique)
- **Timezone** : Europe/Paris
- **Time range** : Last 24 hours (configurable)

### Panel 1 : Statut du dernier scraping

**Type** : Stat  
**Métrique** : `scraping_success`

**Affichage** :
- ✅ Fond VERT si `success = 1`
- ❌ Fond ROUGE si `success = 0`
- Texte : "SUCCESS" ou "FAILED"

**PromQL** :
```promql
scraping_success{job="scraping_intraday"}
```

**Value mapping** :
```
1 → "✅ SUCCESS"
0 → "❌ FAILED"
```

### Panel 2 : Métriques clés (4 colonnes)

**Type** : Stat (4 colonnes)  
**Métriques** : Duration, Scraped, Matched, Updated

**Colonnes** :

1. **Duration (s)** : `scraping_duration_seconds`
2. **Actions scrapées** : `scraping_stocks_scraped_total`
3. **Actions matchées** : `scraping_stocks_matched_count`
4. **Actions mises à jour** : `scraping_stocks_updated_count`

**PromQL** :
```promql
scraping_duration_seconds{job="scraping_intraday"}
scraping_stocks_scraped_total{job="scraping_intraday"}
scraping_stocks_matched_count{job="scraping_intraday"}
scraping_stocks_updated_count{job="scraping_intraday"}
```

### Panel 3 : Taux de match ISIN

**Type** : Gauge  
**Métrique** : `scraping_match_rate_percent`

**Affichage** :
- Aiguille avec arc coloré
- 🔴 ROUGE : < 5% (problème critique)
- 🟠 ORANGE : 5-10% (surveillance)
- 🟢 VERT : > 10% (normal)

**PromQL** :
```promql
scraping_match_rate_percent{job="scraping_intraday"}
```

**Thresholds** :
```
0-5% → Rouge
5-10% → Orange
10-100% → Vert
```

**Valeur normale** : ~16.4% (31 ISINs sur 189 scrapés)

### Panel 4 : Timeline d'exécution

**Type** : Time series  
**Métriques** : Duration + Success sur 24h

**Affichage** :
- Ligne bleue : Durée d'exécution (échelle gauche)
- Ligne verte : Statut success 0/1 (échelle droite)
- Permet de voir l'historique et détecter les anomalies

**PromQL** :
```promql
scraping_duration_seconds{job="scraping_intraday"}
scraping_success{job="scraping_intraday"}
```

**Legend** : Affiche Min, Max, Avg, Current

### Panel 5 : Volume de données traitées

**Type** : Bar chart  
**Métriques** : 5 volumes (scraped, matched, updated, hist_created, hist_updated)

**Affichage** :
- Barres verticales vertes
- Comparaison visuelle des volumes
- Permet de voir si les mises à jour sont cohérentes

**PromQL** :
```promql
scraping_stocks_scraped_total{job="scraping_intraday"}
scraping_stocks_matched_count{job="scraping_intraday"}
scraping_stocks_updated_count{job="scraping_intraday"}
scraping_history_created_count{job="scraping_intraday"}
scraping_history_updated_count{job="scraping_intraday"}
```

### Panel 6 : Tableau récapitulatif

**Type** : Table  
**Toutes les métriques** dans un tableau complet

**Colonnes** :
1. Success (0/1)
2. Durée (s)
3. Actions scrapées
4. Actions matchées
5. Actions MAJ
6. Taux match (%)
7. Hist. créés
8. Hist. MAJ

**Cellules colorées** :
- Success : Vert si 1, Rouge si 0
- Taux match : Vert si >10%, Orange si 5-10%, Rouge si <5%
- Updated : Rouge si 0 et success=1

**PromQL** : Toutes les métriques `scraping_*`

### Personnalisation

**Modifier le refresh** :
1. Cliquer sur l'icône ⚙️ (Dashboard settings)
2. Auto refresh → Changer `30s` vers `10s`, `1m`, etc.

**Modifier la time range** :
1. Sélecteur en haut à droite
2. Choisir : Last 6 hours, Last 7 days, etc.

**Ajouter un panel** :
1. Edit dashboard
2. Add → Visualization
3. Choisir la métrique `scraping_*`
4. Configurer le type de visualisation

---

## 📖 Guide d'utilisation

### Démarrage du système

**1. Lancer tous les services** :
```bash
docker compose up -d
```

**2. Vérifier que tout fonctionne** :
```bash
# Services actifs
docker compose ps

# Logs
docker compose logs -f
```

**3. Accéder aux interfaces** :
- Grafana : http://localhost:3000
- Prometheus : http://localhost:9090
- Pushgateway : http://localhost:9091
- Alertmanager : http://localhost:9093

### Exécution manuelle du scraping

**Ligne de commande** :
```bash
docker compose exec web python manage.py scrape_intraday
```

**Vérifier les métriques** :
```bash
# Dans Pushgateway
curl http://localhost:9091/metrics | grep scraping_

# Dans Prometheus
curl 'http://localhost:9090/api/v1/query?query=scraping_success'
```

**Consulter le dashboard** :
1. Ouvrir http://localhost:3000/d/scraping_intraday/
2. Les métriques se mettent à jour automatiquement
3. Refresh : 30s

### Tests des alertes

**Script de simulation** : `test_scraping_simulation.py`

**Modes disponibles** :
```bash
# Simuler un succès
docker compose exec web python /app/test_scraping_simulation.py success

# Simuler un échec (déclenche ScrapingIntradayFailed après 5min)
docker compose exec web python /app/test_scraping_simulation.py failed

# Simuler un scraping lent (déclenche ScrapingIntradayTooSlow après 3min)
docker compose exec web python /app/test_scraping_simulation.py slow

# Simuler un taux de match faible (déclenche ScrapingMatchRateLow après 15min)
docker compose exec web python /app/test_scraping_simulation.py low_match

# Simuler aucune mise à jour (déclenche ScrapingNoUpdates après 30min)
docker compose exec web python /app/test_scraping_simulation.py no_updates

# Tester tous les scénarios
docker compose exec web python /app/test_scraping_simulation.py all
```

**Vérifier les alertes** :
```bash
# Alertes actives
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.component=="scraping")'

# Ou dans Prometheus UI
open http://localhost:9090/alerts
```

### Consultation des logs

**Logs du scraping** :
```bash
docker compose logs web | grep scraping
```

**Logs APScheduler** :
```bash
docker compose logs web | grep scheduler
```

**Logs Prometheus** :
```bash
docker compose logs prometheus
```

**Logs Grafana** :
```bash
docker compose logs grafana
```

### Monitoring continu

**Vérifications quotidiennes** :

1. **Dashboard Grafana** : Vérifier que le statut est ✅ SUCCESS
2. **Alertes Prometheus** : Aucune alerte active
3. **Taux de match** : Doit rester autour de 16% (31/189)
4. **Durée** : Entre 50-70 secondes normalement

**Vérifications hebdomadaires** :

1. **Timeline 7 jours** : Pas d'anomalies de durée
2. **Logs d'erreurs** : `docker compose logs web | grep ERROR`
3. **Espace disque Prometheus** : `docker system df`

---

## 🔧 Troubleshooting

### Problème 1 : Métriques non visibles dans Grafana

**Symptômes** :
- Dashboard affiche "No data"
- Panels vides

**Diagnostic** :
```bash
# 1. Vérifier Pushgateway
curl http://localhost:9091/metrics | grep scraping_

# 2. Vérifier que Prometheus scrape
curl 'http://localhost:9090/api/v1/query?query=up{job="pushgateway"}'

# 3. Vérifier datasource Grafana
curl http://localhost:3000/api/datasources
```

**Solutions** :

**Si pas de métriques dans Pushgateway** :
```bash
# Relancer un scraping
docker compose exec web python manage.py scrape_intraday
```

**Si Prometheus ne scrape pas** :
```bash
# Vérifier la config Prometheus
docker compose exec prometheus cat /etc/prometheus/prometheus.yml

# Redémarrer Prometheus
docker compose restart prometheus
```

**Si datasource Grafana KO** :
```bash
# Vérifier le fichier datasource
cat grafana/provisioning/datasources/datasource.yml

# Redémarrer Grafana
docker compose restart grafana
```

### Problème 2 : Alertes ne se déclenchent pas

**Symptômes** :
- Simulation d'échec mais pas d'alerte
- État "pending" qui ne passe pas à "firing"

**Diagnostic** :
```bash
# 1. Vérifier que les règles sont chargées
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="scraping_alerts")'

# 2. Vérifier l'état des alertes
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts'

# 3. Vérifier evaluation_interval
docker compose exec prometheus cat /etc/prometheus/prometheus.yml | grep evaluation_interval
```

**Solutions** :

**Si règles non chargées** :
```bash
# Vérifier la syntaxe YAML
docker compose exec prometheus promtool check rules /etc/prometheus/alerts.yml

# Recharger la config
docker compose exec prometheus kill -HUP 1
```

**Si alerte en "pending"** :
- C'est normal : attendre la durée `for` (ex: 5m pour ScrapingIntradayFailed)
- Vérifier avec `curl http://localhost:9090/api/v1/alerts`

**Si evaluation_interval trop long** :
```yaml
# Dans prometheus.yml
global:
  evaluation_interval: 1m  # Évaluer les règles toutes les minutes
```

### Problème 3 : Scraping échoue systématiquement

**Symptômes** :
- `success = 0` à chaque exécution
- Erreur dans les logs

**Diagnostic** :
```bash
# Logs détaillés
docker compose logs web --tail=100 | grep -A 20 "scraping"

# Tester manuellement
docker compose exec web python manage.py scrape_intraday

# Vérifier la connexion à Boursorama
docker compose exec web curl -I https://www.boursorama.com
```

**Solutions possibles** :

**Erreur de connexion** :
```bash
# Vérifier DNS
docker compose exec web ping www.boursorama.com

# Vérifier proxy si nécessaire
docker compose exec web env | grep -i proxy
```

**Erreur de parsing HTML** :
```bash
# Télécharger une page pour analyse
docker compose exec web curl https://www.boursorama.com/bourse/actions/cotations/?quotation_az_filter%5Bmarket%5D=1rPPX5 > test.html

# Vérifier la structure HTML
cat test.html | grep "table"
```

**Erreur de base de données** :
```bash
# Vérifier la connexion à la BDD
docker compose exec web python check_db.py

# Vérifier l'espace disque
df -h db_data/
```

### Problème 4 : Taux de match trop faible

**Symptômes** :
- `match_rate < 5%`
- Peu d'ISINs trouvés

**Diagnostic** :
```bash
# Compter les ISINs en BDD
docker compose exec web python count_isins.py

# Vérifier les ISINs scrapés
docker compose logs web | grep "trouvé"
```

**Solutions** :

**Si BDD vide** :
```bash
# Importer des ISINs
docker compose exec web python manage.py import_stocks
```

**Si structure HTML modifiée** :
1. Analyser une page Boursorama
2. Adapter le parser dans `pea_trading/services/live_scraper.py`
3. Tester à nouveau

### Problème 5 : Dashboard lent ou ne se rafraîchit pas

**Symptômes** :
- Chargement lent
- Refresh ne fonctionne pas

**Solutions** :

**Augmenter les ressources Docker** :
```bash
# Vérifier l'utilisation
docker stats

# Si nécessaire, augmenter dans Docker Desktop
# Settings → Resources → Memory (minimum 4GB)
```

**Réduire la time range** :
- Passer de "Last 24 hours" à "Last 6 hours"
- Moins de données à charger

**Nettoyer les anciennes métriques** :
```bash
# Supprimer les métriques dans Pushgateway
curl -X DELETE http://localhost:9091/metrics/job/scraping_intraday
```

---

## 🔧 Maintenance

### Tâches quotidiennes

**Vérification rapide (2 minutes)** :
```bash
# Dashboard Grafana : statut ✅
open http://localhost:3000/d/scraping_intraday/

# Alertes : aucune active
curl http://localhost:9090/api/v1/alerts | grep '"state":"firing"' | wc -l
# Doit retourner 0
```

### Tâches hebdomadaires

**1. Analyse des logs (5 minutes)** :
```bash
# Erreurs de la semaine
docker compose logs web --since 7d | grep -i error > errors_week.log
cat errors_week.log
```

**2. Vérification des performances** :
```bash
# Durée moyenne sur 7 jours
curl 'http://localhost:9090/api/v1/query?query=avg_over_time(scraping_duration_seconds[7d])'

# Si > 90s : optimiser
```

**3. Nettoyage** :
```bash
# Logs Docker
docker compose logs --tail=0 web

# Images inutilisées
docker system prune -a
```

### Tâches mensuelles

**1. Mise à jour des seuils d'alertes** :

Si le comportement normal change, ajuster les seuils :

```yaml
# prometheus/alerts.yml

# Exemple : augmenter le seuil de durée
- alert: ScrapingIntradayTooSlow
  expr: scraping_duration_seconds{job="scraping_intraday"} > 900  # était 600
```

**2. Backup de la configuration** :
```bash
# Sauvegarder Grafana
docker compose exec grafana backup /var/lib/grafana

# Sauvegarder Prometheus (rétention 15j par défaut)
tar -czf prometheus_backup.tar.gz -C /var/lib/docker/volumes/prometheus_data .
```

**3. Vérification de l'espace disque** :
```bash
# Volumes Docker
docker system df -v

# Ajuster la rétention Prometheus si nécessaire
# Dans prometheus.yml:
# --storage.tsdb.retention.time=30d
```

### Mise à jour du système

**1. Rebuild de l'application** :
```bash
# Après modification du code
docker compose build web
docker compose up -d web
```

**2. Recharger la config Prometheus** :
```bash
# Sans redémarrage
docker compose exec prometheus kill -HUP 1

# Ou redémarrage complet
docker compose restart prometheus
```

**3. Recharger le dashboard Grafana** :
```bash
# Redémarrer pour recharger les provisioning
docker compose restart grafana
```

### Commandes utiles

**Voir toutes les métriques** :
```bash
curl http://localhost:9091/metrics | grep scraping_
```

**Exporter les métriques** :
```bash
# JSON
curl 'http://localhost:9090/api/v1/query?query=scraping_success' | jq > metrics.json

# CSV (via Prometheus)
# Exporter depuis Grafana : Panel → Inspect → Data → Download CSV
```

**Réinitialiser toutes les métriques** :
```bash
# Supprimer le job dans Pushgateway
curl -X DELETE http://localhost:9091/metrics/job/scraping_intraday/job_type/scraping

# Relancer un scraping
docker compose exec web python manage.py scrape_intraday
```

**Recharger tout le système** :
```bash
docker compose down
docker compose up -d
# Attendre 30s que tout démarre
docker compose ps
```

---

## 📚 Ressources

### Documentation

- **Prometheus** : https://prometheus.io/docs/
- **Grafana** : https://grafana.com/docs/
- **Pushgateway** : https://github.com/prometheus/pushgateway
- **Alertmanager** : https://prometheus.io/docs/alerting/latest/alertmanager/

### PromQL utiles

**Taux de succès sur 24h** :
```promql
avg_over_time(scraping_success{job="scraping_intraday"}[24h])
```

**Durée max sur 7 jours** :
```promql
max_over_time(scraping_duration_seconds{job="scraping_intraday"}[7d])
```

**Nombre total de mises à jour sur 24h** :
```promql
sum_over_time(scraping_stocks_updated_count{job="scraping_intraday"}[24h])
```

**Taux de match moyen** :
```promql
avg_over_time(scraping_match_rate_percent{job="scraping_intraday"}[24h])
```

### Contacts et support

- **Logs** : `docker compose logs -f web`
- **Issues** : Créer un ticket sur le repository Git
- **Documentation** : README.md, MONITORING_SYNTHESE.md

---

## 🎉 Conclusion

Le système de monitoring du scraping intraday est maintenant **100% opérationnel** et fournit :

✅ **10 métriques** collectées après chaque scraping  
✅ **5 alertes** automatiques pour détecter les anomalies  
✅ **1 dashboard** Grafana avec 6 panels temps réel  
✅ **Tests** validés (scraping réel + simulations)  
✅ **Persistence** des métriques et historique 24h  

**Prochaines améliorations possibles** :
- Ajouter des notifications email via Alertmanager
- Créer un dashboard d'analyse hebdomadaire/mensuel
- Ajouter des métriques sur les erreurs de parsing
- Intégrer des tests automatisés de régression

---

**Version** : 1.0  
**Date** : Novembre 2025  
**Auteur** : Système de monitoring FlaskFolio
