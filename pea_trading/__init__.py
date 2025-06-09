# pea_trading\__init_.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config.settings import Config
from config.settings import DevConfig, ProdConfig, TestConfig
from prometheus_flask_exporter import PrometheusMetrics

# config hostinger
#from werkzeug.middleware.dispatcher import DispatcherMiddleware



#from datetime import datetime




app = Flask(__name__)

# config hostinger
#app.config['APPLICATION_ROOT'] = '/flask'


#############################################################################
############ CONFIGURATIONS (CAN BE SEPARATE CONFIG.PY FILE) ###############
###########################################################################
app.config.from_object(Config)  # ✅ Charger settings.py (MAIL_* inclus)

from config.settings import DevConfig, ProdConfig, TestConfig

env = os.getenv('FLASK_ENV', 'dev')  # ou 'prod', 'test'
if env == 'prod':
    app.config.from_object(ProdConfig)
elif env == 'test':
    app.config.from_object(TestConfig)
else:
    app.config.from_object(DevConfig)

if not os.getenv("SECRET_KEY"):
    raise RuntimeError("❌ SECRET_KEY manquante dans .env")

if not os.getenv("DATABASE_URL"):
    print("⚠️ DATABASE_URL non défini, fallback sur sqlite:///finance.db")





# Remember you need to set your environment variables at the command line
# when you deploy this to a real website.
# export SECRET_KEY=mysecret
# set SECRET_KEY=mysecret


#################################
### DATABASE SETUPS ############
###############################


# Récupère le dossier actuel (pea_trading)
basedir = os.path.abspath(os.path.dirname(__file__))

# Lit la variable d'environnement (USE_EXTERNAL_DB=1 dans Docker)
USE_EXTERNAL_DB = os.getenv("USE_EXTERNAL_DB", "0") == "1"

# Choisit le bon chemin vers la base en fonction de l’environnement
if USE_EXTERNAL_DB:
    # Dans Docker → on utilise le volume monté dans /db_data
    db_file_path = "/app/db_data/data.sqlite"
else:
    # En local → la base est dans le dossier db_data à la racine du projet
    db_file_path = os.path.join(os.path.dirname(basedir), 'db_data', 'data.sqlite')

# Construit l'URI SQLite compatible avec SQLAlchemy
db_path = f'sqlite:///{db_file_path}'

# Configure SQLAlchemy avec le chemin choisi
app.config['SQLALCHEMY_DATABASE_URI'] = db_path


print("db_path  : ",db_path)    


if USE_EXTERNAL_DB and not os.path.exists("app//db_data/data.sqlite"):
    print("⚠️ Avertissement : /db_data/data.sqlite n'existe pas encore.")



app.config['SQLALCHEMY_DATABASE_URI'] = db_path

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['INIT_BASE'] = False



db = SQLAlchemy(app)
Migrate(app,db)



###########################
#### LOGIN CONFIGS #######
#########################

login_manager = LoginManager()
mail = Mail()

# We can now pass in our app to the login manager
login_manager.init_app(app)
mail.init_app(app) 


# Tell users what view to go to when they need to logiexit

login_manager.login_view = "users.login"


###########################
#### BLUEPRINT CONFIGS #######
#########################

# Import these at the top if you want
# We've imported them here for easy reference
from pea_trading.portfolios.views_portfolio import portfolios
from pea_trading.users.views_users import users

print("coucou1")
from pea_trading.error_pages.handlers import error_pages
print("coucou2")
from pea_trading.admin.views_admin import admin_bp

print("coucou3")

# Register the apps
app.register_blueprint(portfolios)
app.register_blueprint(users)
app.register_blueprint(error_pages)
app.register_blueprint(admin_bp)




# Déplacer ici pour éviter l'import circulaire
from pea_trading.services.yahoo_finance import update_stock_prices, update_historical_prices
from pea_trading.services.portfolio_loader import load_portfolio_data
from pea_trading.portfolios.portfolio import Portfolio
from pea_trading.portfolios.stock import Stock
from pea_trading.users.models import User
from sqlalchemy import inspect




#metrics = PrometheusMetrics(app, path="/metrics")

@app.route("/")
def index():
    return "Hello Metrics!"

# Vérifier si la base de données est initialisée avant de lancer `update_stock_prices`


with app.app_context():
    try:
        # Utiliser l'inspecteur pour vérifier si la table "stock" existe
        inspector = inspect(db.engine)
        if inspector.has_table("portfolios"):
            if not db.session.query(Portfolio).first():  # Vérifie si la table est vide
                print("Première exécution : mise à jour du portefeuille...")
                load_portfolio_data()
                print("Mise à jour du portefeuille terminée !")
        else:
            print("La table portfolios n'existe pas encore. Ignoré.")
    except Exception as e:
        print(f"Erreur lors de la mise à jour du portefeuille : {str(e)}")

    if app.config['INIT_BASE']:
        try:
            inspector = inspect(db.engine)
            if inspector.has_table("stocks"):
                print("📢 Exécution de update_stock_prices()...")
                update_stock_prices()
                print("✅ Mise à jour des actions terminée !")
            else:
                print("⚠️ La table stocks n'existe pas encore. Ignoré.")
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour des actions : {str(e)}")

        try:
            inspector = inspect(db.engine)
            if inspector.has_table("stocks"):
                print("📢 Exécution de update_historical_prices()...")
                update_historical_prices()
                print("✅ Mise à jour des actions terminée !")
            else:
                print("⚠️ La table stocks n'existe pas encore. Ignoré.")
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour des actions : {str(e)}")    

#application = DispatcherMiddleware(None, {'/flask': app})   
#application = app

print("coucou4")