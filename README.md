## ✅ Alertes Prometheus configurées

**8 alertes actives** pour surveiller les jobs cron :

| Alerte | Condition | Sévérité | Description |
|--------|-----------|----------|-------------|
| 🔴 **CronJobFailed** | Job échoue | Critical | Alerte immédiate |
| ⚠️ **CronJobTooSlow** | Durée > 60s | Warning | Performance |
| 📅 **CronJobNotExecutedFor8Days** | Pas exécuté 8j | Warning | Job oublié |
| 🔴 **CronJobNotExecutedFor2Weeks** | Pas exécuté 14j | Critical | Job critique |
| 📊 **CronJobNoRecordsProcessed** | 0 enregistrement | Warning | Données vides |
| 🔥 **AllCronJobsFailed** | 3+ jobs échouent | Critical | Problème système |
| 🕐 **CronJobHistoryTooSlow** | Export > 120s | Warning | Export lent |
| ⏱️ **CronJobStuckRunning** | Job bloqué 5min | Warning | Job planté |

📖 **Documentation complète** : [ALERTES_PROMETHEUS.md](./ALERTES_PROMETHEUS.md)

🔍 **Interfaces** :
- Prometheus Alerts : http://localhost:9090/alerts
- Alertmanager : http://localhost:9093
- Grafana Dashboard : http://localhost:3000


grafana                                               0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp
pea-trading-app                                       0.0.0.0:5000->5000/tcp, [::]:5000->5000/tcp
prometheus                                            0.0.0.0:9090->9090/tcp, [::]:9090->9090/tcp
pushgateway                                           0.0.0.0:9091->9091/tcp, [::]:9091->9091/tcp



🎯 Résumé
Phase	Statut	Durée estimée	Livrables
Phase 1	✅ Terminée	2h30	Code instrumenté + 10 métriques
Phase 2	✅ Terminée	1h	5 alertes Prometheus
Phase 3	🔄 En cours	2-3h	Dashboard Grafana
Phase 4	⏳ À faire	1-2h	Tests de validation
Phase 5	⏳ À faire	1h	Documentation complète
Total restant : ~4-6h de travail

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

---

## 📊 Monitoring du Scraping Intraday

**10 métriques** pour surveiller le scraping quotidien Boursorama :

| Métrique | Description | Seuil alerte |
|----------|-------------|--------------|
| 🎯 **scraping_success** | Succès/Échec du scraping | 0 = échec |
| ⏱️ **scraping_duration_seconds** | Durée d'exécution | > 600s (10min) |
| 📈 **scraping_stocks_scraped_total** | Actions trouvées sur Boursorama | - |
| ✅ **scraping_stocks_matched_count** | Actions matchées (ISIN) | - |
| 💾 **scraping_stocks_updated_count** | Actions mises à jour en BDD | 0 |
| 📊 **scraping_match_rate_percent** | Taux de match (%) | < 10% |
| ➕ **scraping_history_created_count** | Nouveaux historiques créés | - |
| 🔄 **scraping_history_updated_count** | Historiques mis à jour | - |
| 🕐 **scraping_last_execution_timestamp** | Dernière exécution | > 1h |
| ❌ **scraping_error** | Message d'erreur | présent |

📖 **Documentation complète** : [PHASE1_SCRAPING_MONITORING_COMPLETE.md](./PHASE1_SCRAPING_MONITORING_COMPLETE.md)

### 🧪 Tester le monitoring du scraping

```bash
# Simuler un scraping réussi
docker compose exec web python /app/test_scraping_simulation.py success

# Simuler un scraping échoué
docker compose exec web python /app/test_scraping_simulation.py failed

# Simuler un scraping lent (>10min)
docker compose exec web python /app/test_scraping_simulation.py slow

# Simuler un taux de match faible
docker compose exec web python /app/test_scraping_simulation.py low_match

# Tous les scénarios
docker compose exec web python /app/test_scraping_simulation.py all
```

Vérifier les métriques : `curl http://localhost:9091/metrics | grep scraping_`

---

# 📈 FlaskFolio – Gestion de Portefeuilles Boursier

**FlaskFolio** est une application web de gestion de portefeuilles boursier.  
Elle permet de suivre l'évolution des investissements, d'automatiser la récupération des données boursières, d'analyser les performances et de recevoir des alertes par email en fonction de seuils configurés.
Elle fournit un suivi des cours en temps réel, l’import de transactions, ainsi qu’une interface intuitive.

## 🚀 Fonctionnalités principales

- 🔒 Authentification sécurisée (connexion, gestion de profil)
- 📊 Suivi en temps réel des actions via un scrapping du site de boursorama 
- 📊 Suivi hebdomanaire des actions via Yahoo Finance  
- 🔔 Alertes personnalisables par email sur les objectifs de prix atteints
- 📁 Import/export de portefeuilles et transactions (CSV)
- 📉 Analyse des performances et calcul des plus-values
- 🕵️ Visualisation par secteur
- 🗓️ Gestion des jours de bourse ferm
- ⚙️ Tâches planifiées (cron) pour automatiser les exports
- ⚙️ Interface en ligne de commande avec plusieurs commandes utiles pour manipuler la base de données
- 🐳 Déploiement propre avec Docker & Docker Compose

## 🖥️ Technologies utilisées

- **Python** & **Flask** : Backend web léger et extensible
- **SQLAlchemy** : ORM pour la gestion de base de données
- **Flask-Mail** : Notification par email
- **click** : Bibliothèque CLI utilisée par Flask pour ajouter des options et commandes
- **WTForms** : Gestion des formulaires
- **Bootstrap** : Charte graphique sobre et responsive
- **Docker / Docker Compose** : Conteneurisation de l’application


## 🛠️ Stack technique

- **Backend** : Python, Flask, SQLAlchemy
- **Frontend** : Jinja2 + Bootstrap
- **Stock Data** : Yahoo Finance
- **Mailing** : Flask-Mail (SMTP Gmail)
- **Conteneurisation** : Docker + Docker Compose

## 🧠 Architecture

- `pea_trading/` : Code principal de l'application (modèles, vues, services)
- `config/` : Configuration Flask et des valeurs boursières à suivre
- `templates/` : Templates HTML pour l’interface utilisateur
- `static/` : Fichiers statiques (CSS, images, fichiers CSV)
- `utils/` : Utilitaires tels que l'envoi d'emails et la gestion des jours fériés


## 🧩 Structure du projet

```
.
├── 📄 Fichiers principaux
│   ├── .env                          # Variables d'environnement (SECRET_KEY, DATABASE_URL, MAIL_*)
│   ├── .dockerignore                 # Exclusions pour le build Docker
│   ├── app.py                        # Point d'entrée de l'application
│   ├── check_db.py                   # Vérification de l'état de la base de données
│   ├── manage.py                     # CLI avec commandes utiles (update, export, import, logs, etc.)
│   ├── tasks_scheduler.py            # Configuration des tâches planifiées (legacy)
│   ├── requirements.txt              # Dépendances Python
│   ├── README.md                     # Documentation du projet
│   ├── LICENSE                       # Licence du projet
│
├── 🐳 Docker
│   ├── dockerfile                    # Image Docker de l'application
│   ├── docker-compose.yml            # Orchestration des services (web, prometheus, grafana)
│   ├── docker-compose-classique.yml  # Configuration alternative
│   ├── cleanup_container.sh          # Script de nettoyage des conteneurs
│   ├── cleanup_temp_files.sh         # Script de nettoyage des fichiers temporaires
│
├── ⚙️ Configuration
│   ├── config/
│   │   ├── settings.py               # Configuration Flask (Dev, Prod, Test)
│   │   └── stocks.py                 # Configuration des actions suivies
│   ├── cron_jobs.txt                 # Tâches cron pour exports hebdomadaires
│   └── prometheus.yml                # Configuration Prometheus (monitoring)
│
├── 🗄️ Base de données
│   ├── db_data/                      # 📁 Volume Docker - Base SQLite
│   │   └── data.sqlite               # Base de données principale
│   └── migrations/                   # Migrations Alembic
│       ├── alembic.ini
│       ├── env.py
│       └── versions/                 # Historique des migrations
│           ├── 55bed6705752_initial_migration.py
│           ├── 7d29813a6974_ajout_des_colonnes_max_min_et_target.py
│           └── 204481c175d9_ajout_transaction_et_cashmovement.py
│
├── 📊 Logs et exports
│   ├── logs_local/                   # 📁 Volume Docker - Logs personnalisés
│   │   ├── .gitkeep
│   │   ├── README.md                 # Documentation des logs
│   │   ├── intraday.log              # Logs scraping Boursorama
│   │   ├── yfinance.log              # Logs Yahoo Finance
│   │   └── manage.log                # Logs des commandes manage.py
│   ├── exports_local/                # 📁 Volume Docker - Exports CSV
│   └── uploads_local/                # 📁 Volume Docker - Uploads utilisateurs
│
├── 🧪 Tests
│   └── tests/
│       ├── __init__.py
│       └── test_app.py               # Tests unitaires
│
├── 📸 Documentation
│   └── ImagesMd/                     # Captures d'écran pour le README
│       ├── FlaskFolio_admin.jpg
│       ├── FlaskFolio_login.jpg
│       └── ...
│
└── 🎯 Application principale
    └── pea_trading/
        ├── __init__.py               # Initialisation Flask, DB, Scheduler
        │
        ├── admin/                    # 👤 Module d'administration
        │   ├── __init__.py
        │   ├── forms_admin.py        # Formulaires admin
        │   └── views_admin.py        # Routes admin (/admin/*)
        │
        ├── portfolios/               # 📊 Gestion des portefeuilles
        │   ├── portfolio.py          # Modèles Portfolio, Position, Transaction, CashMovement
        │   ├── stock.py              # Modèles Stock, StockPriceHistory
        │   └── views_portfolio.py    # Routes portefeuilles (/portfolios/*)
        │
        ├── users/                    # 🔐 Gestion des utilisateurs
        │   ├── __init__.py
        │   ├── forms_users.py        # Formulaires (login, register, update)
        │   ├── models.py             # Modèle User
        │   ├── picture_handler.py    # Gestion des photos de profil
        │   └── views_users.py        # Routes utilisateurs (/login, /register, etc.)
        │
        ├── services/                 # 🔧 Services métier
        │   ├── alertes.py            # Détection des alertes de prix
        │   ├── export_utils.py       # Export CSV (positions, transactions, cash)
        │   ├── import_utils.py       # Import CSV
        │   ├── finance_ops.py        # Opérations financières (calculs de performance)
        │   ├── live_scraper.py       # 🌐 Scraping Boursorama (intraday + logger)
        │   ├── yahoo_finance.py      # 📈 API Yahoo Finance (prix + historique + logger)
        │   ├── technical_indicators.py # Indicateurs techniques (Ichimoku, etc.)
        │   ├── portfolio_loader.py   # Chargement initial des données
        │   ├── scheduler_jobs.py     # Jobs planifiés (alertes, update, scraping)
        │   └── scheduler_utils.py    # Utilitaires scheduler (APScheduler)
        │
        ├── utils/                    # 🛠️ Utilitaires
        │   └── notifications.py      # Envoi d'emails, gestion jours fériés
        │
        ├── error_pages/              # ⚠️ Gestion des erreurs
        │   └── handlers.py           # Handlers 404, 500, etc.
        │
        ├── static/                   # 📁 Fichiers statiques
        │   ├── master.css            # Feuille de style principale
        │   ├── master.js             # Scripts JavaScript
        │   ├── exports/              # 📁 Volume Docker - Exports CSV
        │   ├── uploads/              # 📁 Volume Docker - Uploads
        │   ├── profile_pics/         # Photos de profil des utilisateurs
        │   └── logs/                 # 📁 Volume Docker - Logs scheduler
        │       ├── scheduler.log     # Logs du scheduler APScheduler
        │       └── manage.log        # Logs des commandes manage.py
        │
        └── templates/                # 🎨 Templates Jinja2
            ├── base.html             # Template de base
            ├── index.html            # Page d'accueil / Dashboard
            ├── login.html, register.html, account.html
            ├── select_portfolio.html # Sélection du portefeuille
            ├── portfolio_history.html, stock_history.html
            ├── transactions.html, liquidites.html
            ├── admin*.html           # Templates admin
            ├── pagination.html       # Composant pagination
            ├── emails/               # Templates d'emails
            │   └── alertes.html      # Email d'alertes
            └── error_pages/          # Pages d'erreur
                ├── 404.html
                └── 500.html
```

### 📁 Volumes Docker montés

Les dossiers suivants sont montés comme volumes persistants :
- `db_data/` → `/app/db_data` : Base de données SQLite
- `logs_local/` → `/app/logs_local` ET `/app/pea_trading/static/logs` : Tous les logs
- `exports_local/` → `/app/pea_trading/static/exports` : Exports CSV
- `uploads_local/` → `/app/pea_trading/static/uploads` : Fichiers uploadés

---
🔁 Tâches planifiées avec APScheduler
Ce projet utilise APScheduler pour planifier des tâches récurrentes comme :

🔔 la détection d’alertes,

📈 la mise à jour des données boursières (prix et historique) hebdomadairs et quoditiennes

✅ l’administration des taches est possible via une page dédiée /admin/scheduler.

---


##  👤 Guide utilisateur

###  📝 1. Créer un compte

- Se rendre sur `/register`
- Fournir email, nom d'utilisateur et mot de passe

###  🔐 2. Se connecter

- Accéder à `/login`
- Entrer vos identifiants pour accéder au tableau de bord
![jpg](/ImagesMd/FlaskFolio_login.jpg)

###  📥 3. administrer le site

- Cliquer sur 'Administration'
![jpg](/ImagesMd/FlaskFolio_admin.jpg)

###  🔔 4 . Suprimmer ou modifier des transactions

- Cliquer sur 'Administration' puis 'Voir toute les transactions'

![jpg](/ImagesMd/FlaskFolio_admin_transactions.jpg)

###  🔔 5 . Suprimmer des mouvements d'espèces

- Cliquer sur 'Administration' puis 'Voir toutes les liquidités'
![jpg](/ImagesMd/FlaskFolio_admin_liquidites.jpg)

###  🔔 6 . Visualiser le Scheduler

- Visualiser l'état du scheduler et les taches en cours
- Il est posssible de suspendre, d'arreter ou de relancer une tache
![jpg](/ImagesMd/FlaskFolio_admin_Scheduler.jpg)

###  🔔 7 . Lancer le Scheduler

Il est possible de lancer le Scheduler ou de relancer à partir du menu d'administrattion
![jpg](/ImagesMd/FlaskFolio_admin_RelScheduler.jpg)

###  📥 8. Valeurs suivies

- Cliquer sur 'Administration'
- Formulaire de saisie d'une nouvelle valeur à suivre
![jpg](/ImagesMd/FlaskFolio_valasuivre.jpg)
...
...
...
![jpg](/ImagesMd/FlaskFolio_valasuivre_2.jpg)

- Liste des opérations possibles : 
  - enregistrer une nouvelle valeur
  - exporter la liste des actions suivies au format csv
  - exporter la isite de l'historique complet ds valeurs des actions suivies au format csv
  - importer la liste des actions suivies au format csv
  - importer la isite de l'historique complet ds valeurs des actions suivies au format csv

###  📈 9. Ajouter une action à un portefeuille

- Cliquer sur 'Administration'
- Formulaire de saisie d'une nouvelle valeur à ajouter au portefeuille selectionné
![jpg](/ImagesMd/FlaskFolio_portefeuille.jpg)
...
...
...
![jpg](/ImagesMd/FlaskFolio_portefeuille_2.jpg)

- Liste des opérations possibles sur le portefeuille : 
  - ajouter une nouvelle action
  - supprimer une action
  - renforcer une action
  - alleger une action
  - exporter la liste des actions du portefeuille au format csv
  - importer la liste des actions du portefeuille au format csv
  

###  🔔 10. Ajouter un transaction à un portefeuille

- Les transactions s'ajoutent automatiquement lors de l'ajout d'une opération sur un portefeuille, mais il est possible d'ajouter des transactions individuelles.
![jpg](/ImagesMd/FlaskFolio_ajout_transaction.jpg)

###  🔔 11 . Ajouter un mouvement de trésorerie à un portefeuille

- Les transactions s'ajoutent automatiquement lors de l'ajout d'une opération sur un portefeuille, mais il est aussi possibled'ajouter des transactions individuelles comme par exemple les saisies de dividendes.

![jpg](/ImagesMd/FlaskFolio_ajout_cash.jpg)

---

##  **Installation locale**

1. **Cloner le dépôt**

```bash
git clone git@github.com:ManDes71/FlaskFolio-gestion-de-portefeuilles.git
cd FlaskFolio-gestion-de-portefeuilles
````

2. **Configurer l’environnement**

Créer un fichier `.env` à la racine du projet avec les variables suivantes :

```bash
FLASK_ENV=dev
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///finance.db
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-email-password
```

## **Démarrer l'application avec Docker**

> ℹ️ **Note** : Ce projet utilise **Docker Compose V2**. La commande est `docker compose` (avec un espace) au lieu de `docker-compose` (avec un tiret).

```bash
# Arrêter les conteneurs existants
docker compose down

# Construire l'image
docker compose build

# Démarrer en arrière-plan
docker compose up -d
```


## Lancer des commandes en shell interactif
```bash
# Accéder au conteneur en mode interactif
docker compose exec web bash

# Puis exécuter les commandes manage.py :
python manage.py import_portfolio_positions_csv "PEA" portefeuille_export_PEA.csv 
python manage.py export_transactions_csv "PEA" --output "transactions_export_PEA.csv"
python manage.py export_transactions_csv "PEA-PME" --output "transactions_export_PEA-PME.csv"
python manage.py export_cash_mouvements_csv "PEA" --output "cash_mouvements_export_PEA.csv"
python manage.py export_cash_mouvements_csv "PEA-PME" --output "cash_mouvements_export_PEA-PME.csv"

# Sortir du conteneur
exit
```

## Consulter les logs

```bash
# Logs en temps réel
docker compose logs -f web

# Dernières 100 lignes
docker compose logs --tail=100 web
```

L'application sera disponible sur `http://127.0.0.1:5000/portfolios`.

http://localhost:9090/
http://localhost:9093  -> alertmanager
http://localhost:3000  -> grafana
http://localhost:3000/playlists/play/cf2udm3mw01kwf?kiosk=true-> grafana

Ce fichier `manage.py` est un **script de gestion personnalisé** pour une application Flask appelée `pea_trading`. Il utilise **Click** (via `flask.cli.FlaskGroup`) pour proposer une **interface en ligne de commande** avec plusieurs commandes utiles pour le développement, l’administration et les tests de l’application.

---

## 📌 Commandes définies

---

### ▶️ `run` — Lancer le serveur Flask

```python
@cli.command("run")
@click.option("--env", default="dev", help="Environnement (dev, prod, test)")
@click.option("--host", default="127.0.0.1", help="Hôte à utiliser")
@click.option("--port", default=5000, help="Port à utiliser")
def run_server(env, host, port):
```

* Définit une commande `run` qui permet de démarrer le serveur Flask.
* Change la variable d’environnement `FLASK_ENV` (ex : `dev`, `prod`).
* Utilise les paramètres fournis pour l’hôte et le port.

Exemple d’utilisation :

```bash
python manage.py run --env=prod --host=0.0.0.0 --port=8000
```
ou avec docker :

```bash
docker compose exec web python manage.py export_transactions_csv "PEA-PME" --output "static/exports/transactions_export_PEA-PME.csv"
```

---

### 🔁 `update` — Mise à jour des données boursières

```python
@cli.command("update")
@click.option("--historique", is_flag=True, help="Inclure la mise à jour historique")
def update_data(historique):
```

* Appelle `update_stock_prices()` pour mettre à jour les **cours actuels**.
* Si `--historique` est passé, met aussi à jour les **données historiques**.

Exemple :

```bash
python manage.py update --historique
```

---

### 🛠 `init-db` — Initialisation du portefeuille

```python
@cli.command("init-db")
@click.option("--force", is_flag=True, help="Recharge le portefeuille même si non vide")
def init_db(force):
```

* Vérifie si la table `portfolios` existe.
* Si elle est vide ou si `--force` est utilisé, appelle `load_portfolio_data()` pour charger les données de base.

Exemple :

```bash
python manage.py init-db --force
```

---

### 🛠 `change_password` — changement de mot de passe

```python
@cli.command("change_password")
@click.argument("email")
def change_password(email):
```

* Change le mot de passe d'un utilisateur.
toto@24 sur gmail


Exemple :

```bash
python  manage.py change_password user@example.com
```
ou avec docker :

```bash
docker compose exec web python manage.py change_password user@example.com
```
---

### 🛠 `list_stock_duplicates` — doublons dans la table Stock
```python
@cli.command("list_stock_duplicates")
def list_stock_duplicates():
```

* Liste les doublons dans la table Stock (symbol ou ISIN en double).


Exemple :

```bash
python  manage.py list_stock_duplicates
```
---

### 🛠 `list_history_duplicates` — doublons dans la table StockPriceHistory

```python
@cli.command("list_history_duplicates")
def list_history_duplicates():
```

* Liste les doublons dans StockPriceHistory (même stock_id + date).


Exemple :

```bash
python  manage.py list_history_duplicates
```
---

### 🛠 `delete_history_duplicates` — suppression doublons dans la table StockPriceHistory

```python
@cli.command("ldelete_history_duplicates"")
def delete_history_duplicates():
```

* Supprime les doublons dans StockPriceHistory (garde le plus récent ID).


Exemple :

```bash
python  manage.py delete_history_duplicates
```

---

### 🛠 `export_all_stocks_csv` — export de la liste des actions suivies

```python
@cli.command("export_all_stocks_csv"")
def export_all_stocks_csv():
```

* exportation en fichier csv de la liste totale des actions suivies : stocks_export.csv


Exemple :

```bash
python  manage.py export_all_stocks_csv
```

---

### 🛠 `export_all_stock_history_csv` — export de l'historique des actions suivies

```python
@cli.command("export_all_stock_history_csv")
def export_all_stock_history_csv():
```

* exportation en fichier csv de l'historique des valeurs des actions suivies : historique_stocks.csv


Exemple :

```bash
python  manage.py export_all_stock_history_csv
```
---

### 🛠 `import_stocks_csv` — import de la liste des actions suivies

```python
@cli.command("import_stocks_csv")
def import_stocks_csv():
```

* importation en fichier csv de la liste totale des actions suivies : stocks_export.csv


Exemple :

```bash
python  manage.py import_stocks_csv
```

---

### 🛠 `import_all_stock_history_csv` — import de l'historique des actions suivies

```python
@cli.command("import_all_stock_history_csv")
def import_all_stock_history_csv():
```

* Importe tout l’historique des valeurs depuis un fichier CSV : historique_stocks.csv


Exemple :

```bash
python  manage.py import_all_stock_history_csv
```
---

### 🛠 `export_portfolio_csv` — ixporte les positions d'un portefeuille

```python
@cli.command("export_portfolio_csv")
@click.argument("portfolio_name")
@click.option("--output", default=None, help="Nom du fichier de sortie (par défaut : portfolio_export_<nom>_<timestamp>.csv)")
def export_portfolio_csv(portfolio_name, output):
```

* Exporte les positions d'un portefeuille (symbole, ISIN, nom, quantité, prix d'achat, secteur) vers un CSV.
  ex : portefeuille_export_PEA_20250531_210403.csv

Exemple :

```bash
python  manage.py export_portfolio_csv "PEA"
python  manage.py export_portfolio_csv "PEA" --output export_portfolio_csv
```

---

### 🛠 `export_transactions_csv` — Exporte les transactions d'un portefeuille 

```python
@cli.command("export_transactions_csv")
@click.argument("portfolio_name")
@click.option("--output", default=None, help="Nom du fichier de sortie (par défaut : transactions_<nom>_<timestamp>.csv)")
def export_transactions_csv(portfolio_name, output):
```

* Exporte les transactions d'un portefeuille vers un fichier CSV.
  ex : transactions_PEA_20250531_210335.csv

Exemple :

```bash
    python manage.py export_transactions_csv "PEA"
    python manage.py export_transactions_csv "PEA-PME" --output "transactions_export_PEA-PME.csv"

    docker compose exec web python manage.py export_transactions_csv "PEA-PME" --output "static/exports/transactions_export_PEA-PME.csv"
```

---

### 🛠 `export_cash_mouvements_csv` — Exporte les mouvements de trésorerie d'un portefeuille

```python
@cli.command("export_cash_mouvements_csv")
@click.argument("portfolio_name")
@click.option("--output", default=None, help="Nom du fichier de sortie (par défaut : cash_movements_<nom>_<timestamp>.csv)")
def export_cash_movements_csv(portfolio_name, output):
```

* Exporte les mouvements de trésorerie d'un portefeuille vers un CSV.
  ex : cash_mouvements_PEA-PME_20250601_180906.csv

Exemple :

```bash
    python manage.py export_cash_mouvements_csv "PEA"
    python manage.py export_cash_mouvements_csv "PEA-PME" --output "cash_mouvements_export_PEA-PME.csv"

```
---

### 🛠 `import_portfolio_positions_csv` — importe les positions d'un portefeuille

```python
@cli.command("import_portfolio_positions_csv")
@click.argument("portfolio_name")
@click.argument("filename")
def import_portfolio_positions_csv(portfolio_name, filename):
```

* Importe les positions d'un portefeuille (symbole, ISIN, nom, quantité, prix d'achat, secteur) depuis un CSV.
 

Exemple :

```bash
    python manage.py import_portfolio_positions_csv "PEA" portefeuille_export_PEA_20250531_214843.csv 
```
---

### 🛠 `import_transactions_csv` — importe les positions d'un portefeuille

```python
cli.command("import_transactions_csv")
@click.argument("portfolio_name")
@click.argument("filename")
def import_transactions_csv(portfolio_name, filename):
```

* Importe les transactions d'un portefeuille depuis un fichier CSV.
 

Exemple :

```bash
    python  manage.py import_transactions_csv "PEA-PME" transactions_PEA-PME_20250531_223800.csv       
```
---

### 🛠 `import_cash_movements_csv` — importe les positions d'un portefeuille

```python
@cli.command("import_cash_movements_csv")
@click.argument("portfolio_name")
@click.argument("filename")
def import_cash_movements_csv(portfolio_name, filename):
```

* Importe les mouvements de trésorerie d'un portefeuille depuis un fichier CSV.
 

Exemple :

```bash
    python  manage.py import_cash_movements_csv "PEA-PME" cash_mouvements_PEA-PME_20250531_223806.csv      
```
---

### 📅 `show_scheduler` — Afficher les tâches planifiées (scheduler jobs)

```python
@cli.command("show_scheduler")
def show_scheduler():
```

* Affiche les tâches planifiées du scheduler APScheduler.
* Liste les jobs avec leurs ID, nom, fonction, déclencheur et prochaine exécution.
* Utile pour vérifier que les jobs automatiques sont bien configurés (alertes, mise à jour des cours, scraping).

Exemple :

```bash
python manage.py show_scheduler

# Depuis Docker :
docker compose exec web python manage.py show_scheduler
```

**Sortie exemple :**
```
📅 === Tâches planifiées (3 job(s)) ===

🔹 Job ID: job_alertes
   Nom: job_alertes
   Fonction: job_alertes
   Déclencheur: day_of_week=0-4, hour=18, minute=30
   Prochaine exécution: 2025-11-03 18:30:00 UTC

🔹 Job ID: job_update_stocks
   Nom: job_update_stocks
   Fonction: job_update_stocks
   Déclencheur: day_of_week=0-4, hour=8, minute=0
   Prochaine exécution: 2025-11-03 08:00:00 UTC

🔹 Job ID: job_scraping_intraday
   Nom: job_scraping_intraday
   Fonction: job_scraping_intraday
   Déclencheur: day_of_week=0-4, hour=9-17, minute=0
   Prochaine exécution: 2025-11-01 15:00:00 UTC
```

---

### ⏰ `show_cron` — Afficher les tâches cron configurées

```python
@cli.command("show_cron")
def show_cron():
```

* Affiche les tâches cron définies dans le fichier `cron_jobs.txt`.
* Parse et explique en français la planification de chaque tâche.
* Utile pour vérifier les exports automatiques hebdomadaires.

Exemple :

```bash
python manage.py show_cron

# Depuis Docker :
docker compose exec web python manage.py show_cron
```

**Sortie exemple :**
```
⏰ === Tâches CRON configurées ===

🔹 Planification: 0 20 * * 0
   Commande: cd /app && /usr/local/bin/python /app/manage.py export_transactions_csv "PEA" --output "static/exports/transactions_export_PEA.csv"
   📝 à la minute 0 à 20h le dimanche

🔹 Planification: 5 20 * * 0
   Commande: cd /app && /usr/local/bin/python /app/manage.py export_cash_mouvements_csv "PEA" --output "static/exports/cash_mouvements_export_PEA.csv"
   📝 à la minute 5 à 20h le dimanche
```

---

### ✅ `test` — Lancer les tests unitaires

```python
@cli.command("test")
def run_tests():
```

* Utilise `unittest` pour découvrir tous les tests dans le dossier `tests/`.
* Affiche les résultats et retourne un code de sortie `1` si échec (utile pour CI/CD).

Exemple :

```bash
python manage.py test
```

---

### 🐚 `shell` — Ouvrir un shell interactif

```python
@cli.command("shell")
def interactive_shell():
```

* Lance un shell Python interactif avec accès à `app` et `db`.
* Utile pour tester des requêtes ou manipuler la base en direct.

Exemple :

```bash
python manage.py shell
```

## 🙌 Contribuer

Les contributions sont les bienvenues ! Forkez le repo, créez une branche, soumettez une PR.

## 📄 Licence

Ce projet est sous licence MIT.

---

✨ *PEA Trading – Prenez le contrôle de vos investissements !*

```

---

Souhaites-tu que je crée directement ce fichier dans le dépôt local du projet (dans un fichier `README.md`) ou que je le modifie ensuite avec des sections supplémentaires (par exemple pour un guide utilisateur, une documentation API ou des captures d’écran) ?
```
