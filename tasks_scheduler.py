# scheduler.py
# scheduler.py

from pea_trading import app, db, mail
from pea_trading.services.alertes import detecter_alertes
from pea_trading.utils.notifications import envoyer_email_alertes, is_today_closed
from pea_trading.portfolios.portfolio import Portfolio
from pea_trading.portfolios.stock import Stock, StockPriceHistory
from pea_trading.users.models import User
from pea_trading.services.yahoo_finance import update_stock_prices, update_historical_prices
from pea_trading.services.live_scraper import  get_stock_prices, get_stock_info

from sqlalchemy import and_, func


from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import os
import logging
import time
import pytz
paris_tz = pytz.timezone('Europe/Paris')

# 📂 Assure-toi que le dossier logs existe
log_dir = os.path.join(os.path.dirname(__file__), 'pea_trading','static', 'logs')
os.makedirs(log_dir, exist_ok=True)

# 📄 Fichier de log
log_file = os.path.join(log_dir, 'scheduler.log')

# ⚙️ Configuration du logger
logger = logging.getLogger("scheduler")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)

# Ajoute le handler s'il n'y en a pas déjà (évite les doublons en cas d'import multiples)
if not logger.handlers:
    logger.addHandler(file_handler)

# Initialisation du scheduler
scheduler = BackgroundScheduler()




### 🔁 JOB 1 : Alertes
def job_alertes():
    if is_today_closed():
        print("📅 Aujourd’hui est un jour férié. Pas d’envoi d’alertes.")
        return
    with app.app_context():
        print(f"[{datetime.now()}] 🔁 Lancement du job d'alertes")
        logger.info(f"🔁 Lancement du job d'alertes")
        portfolios = Portfolio.query.all()
        for portfolio in portfolios:
            user = User.query.get(portfolio.user_id)
            if not user:
                continue
            print(f"🔍 Portefeuille {portfolio.name} (utilisateur : {user.email})")
            logger.info(f"🔍 Portefeuille {portfolio.name} pour {user.email}")
            alertes = detecter_alertes(portfolio)
            if alertes["alertes_vente"] or alertes["alertes_achat"]:
                envoyer_email_alertes(user.email, portfolio, alertes, app, mail)
                logger.info(f"📧 Email envoyé avec alertes pour {user.email}")

### 📈 JOB 2 : Mise à jour des données boursières hebdomadaire
def job_update_stocks():
    with app.app_context():
        print(f"[{datetime.now()}] 📊 Mise à jour hebdomadaire des valeurs boursières")
        logger.info(f"📊 Lancement MAJ boursière")
        try:
            update_stock_prices()
            print("✅ Prix actuels mis à jour.")
            logger.info("✅ Prix mis à jour")
        except Exception as e:
            print(f"❌ Erreur update_stock_prices : {e}")
            logger.error(f"❌ Erreur update_stock_prices : {e}")

        try:
            update_historical_prices()
            print("✅ Historique mis à jour.")
            logger.info("✅ Historique mis à jour")
        except Exception as e:
            print(f"❌ Erreur update_historical_prices : {e}")
            logger.error(f"❌ update_historical_price : {e}")

def job_scraping_intraday():
    if is_today_closed():
        print("📅 Aujourd’hui est un jour férié. Pas de scraping.")
        return
    print(f"[{datetime.now()}] ⚡ Job scraping Boursorama en cours...")
    with app.app_context():
        today = datetime.now().date()
        updated = 0

        # Récupère toutes les lettres (A-Z)
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            stocks = get_stock_prices(letter)

            for stock in stocks:
                #name = stock.get("name")
                price = stock.get("price")
                code = stock.get("symbol")
                ouverture = stock.get("ouverture")
                plus_haut = stock.get("plus_haut")
                plus_bas = stock.get("plus_bas")
                cloture = stock.get("cloture")
                volume = stock.get("volume")
                codeisin, code_yahoo, sector = get_stock_info(code)
                print(codeisin, code_yahoo, sector)
                isin = codeisin
      
                try:
                    stock = Stock.query.filter_by(isin=isin).first()
                    if stock:
                        print(f"✅ {isin} trouvé")
                        stock.current_price = price
                        stock.last_updated = datetime.now()
                        updated += 1

                        # Ajout ou mise à jour de StockPriceHistory
                        #existing = StockPriceHistory.query.filter_by(stock_id=stock.id, date=today).first()
                        with db.session.no_autoflush:
                            existing = StockPriceHistory.query.filter(
                                and_(
                                    StockPriceHistory.stock_id == stock.id,
                                    func.date(StockPriceHistory.date) == today
                                )
                            ).first()
                        if existing:
                            existing.open_price = ouverture
                            existing.high_price = plus_haut
                            existing.low_price = plus_bas
                            existing.close_price = cloture
                            existing.last_updated = datetime.now()
                            existing.volume = volume
                            logger.info(f"✅ {isin} à jour")
                            print(f"✅ {isin} à jour")
                        else:
                            history = StockPriceHistory(
                                stock_id=stock.id,
                                date=today,
                                open_price=ouverture,
                                high_price=plus_haut,
                                low_price=plus_bas,
                                close_price=cloture,
                                volume=volume,
                            )
                            db.session.add(history)
                            logger.info(f"✅ {isin} créée)")
                            print(f"✅ {isin} créée)")
                    else:
                        print(f"❌ {isin} non trouvé")
                    time.sleep(0.1)  # 🔄 Soulage SQLite

                except Exception as e:
                    #print(f"❌ Erreur pour {isin} : {e}")
                    logger.error(f"❌ Erreur pour {isin} : {e}")   

        try:
            db.session.commit()
            print(f"✅ Scraping terminé : {updated} valeurs mises à jour.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Commit final échoué : {e}")
            print(f"❌ Commit final échoué : {e}")
        print(f"✅ Scraping terminé : {updated} valeurs mises à jour (cours + historique).")
        #stocks = Stock.query.all()
        #for s in stocks:
        #    print(f"Stock en base : {s.name} -{s.isin}-")
        #    print(f"isin (en base): -{s.isin}- (len={len(s.isin)})")
      

# 🚦 Démarrage du scheduler uniquement dans le process principal
if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    print("📅 Configuration du scheduler...")

    if scheduler.get_job("job_alertes"):
        scheduler.remove_job("job_alertes")

    # Lundi–vendredi, toutes les 10 min entre 9h et 18h
    scheduler.add_job(
        job_alertes,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour='9-18',
            minute='*/50',
            timezone=paris_tz 
        ),
        id="job_alertes",
        misfire_grace_time=300
    )
    
    if not scheduler.get_job("job_update_stocks"):
        scheduler.add_job(job_update_stocks, CronTrigger(day_of_week='sat', hour=8, minute=0, timezone=paris_tz ), id="job_update_stocks",
    misfire_grace_time=600)
        
    if scheduler.get_job("job_scraping_intraday"):
        scheduler.remove_job("job_scraping_intraday")

    # Lundi–vendredi, toutes les 15 min entre 9h30 et 18h30
    scheduler.add_job(
        job_scraping_intraday,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour='9-18',
            minute='*/30',
            timezone=paris_tz 
        ),
        id="job_scraping_intraday",
        misfire_grace_time=300
    )    

    scheduler.start()
    print("✅ APScheduler lancé avec jobs : alertes (1h) + MAJ boursière (samedi 8h)")

# 📤 Exposer l'instance de scheduler à l'extérieur
scheduler_instance = scheduler
