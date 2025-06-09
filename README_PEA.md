Voici un exemple de fichier `README.md` que tu peux utiliser pour publier ton projet sur GitHub. Il met en valeur les fonctionnalités, technologies et objectifs de ton application de gestion de portefeuille boursier :

---

````markdown
# 📈 FlaskFolio – Gestion de Portefeuille Boursier

**FlaskFolio** est une application web de gestion de portefeuille boursier.  
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


## 🧩 Structure 

```
.
├── app.py
├── manage.py
├── .env
├── config/
│   └── settings.py
├── pea_trading/
│   ├── __init__.py
│   ├── users/
│   ├── portfolios/
│   ├── services/
│   └── templates/
├── tests/
│   └── test_dummy.py



---
🔁 Tâches planifiées avec APScheduler
Ce projet utilise APScheduler pour planifier des tâches récurrentes comme :

🔔 la détection d’alertes,

📈 la mise à jour des données boursières (prix et historique) hebdomadairs et quoditiennes

✅ l’administration des taches est possible via une page dédiée /admin/scheduler.

---

---

## 👤 Guide utilisateur

### 📝 1. Créer un compte

- Se rendre sur `/register`
- Fournir email, nom d'utilisateur et mot de passe

### 🔐 2. Se connecter

- Accéder à `/login`
- Entrer vos identifiants pour accéder au tableau de bord

### 📥 3. Importer un portefeuille

- Aller dans la section “Importer”
- Sélectionner un fichier `.csv` contenant les transactions ou mouvements de cash

### 📈 4. Suivre l’évolution des actions

- Visualisation des performances
- Filtres par secteur, actions actives ou en veille

### 🔔 5. Recevoir des alertes

- Les seuils de prix sont définis dans le fichier de config (`stocks.py`)
- Vous recevrez un email si un seuil est franchi (achat ou vente)

### 🔔 10 . Suprimmer des transactiond

- Les seuils de prix sont définis dans le fichier de config (`stocks.py`)
- Vous recevrez un email si un seuil est franchi (achat ou vente)
![png](/ImagesMd/FlaskFolio_admin_liquidites.jpg)

---

## **Installation locale**

1. **Cloner le dépôt**

```bash
git clone https://github.com/votre-utilisateur/pea-trading.git
cd pea-trading
````

2. **Configurer l’environnement**

Créer un fichier `.env` à la racine du projet avec les variables suivantes :

```
FLASK_ENV=dev
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///finance.db
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-email-password
```

## **Démarrer l’application avec Docker**

```bash
docker-compose up --build
```

L'application sera disponible sur `http://127.0.0.1:5000`.

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
docker exec -it pea-trading-app python manage.py export_transactions_csv "PEA-PME" --output "static/exports/transactions_export_PEA-PME.csv"
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


Exemple :

```bash
python  manage.py change_password user@example.com
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

    docker exec -it pea-trading-app python manage.py export_transactions_csv "PEA-PME" --output "static/exports/transactions_export_PEA-PME.csv"
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
