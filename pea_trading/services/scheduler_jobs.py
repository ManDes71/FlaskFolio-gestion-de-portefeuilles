#from tasks_scheduler import job_alertes, job_update_stocks, job_scraping_intraday
#from apscheduler.triggers.cron import CronTrigger
from pea_trading.utils.notifications import envoyer_email_alertes, is_today_closed
from pea_trading.services.alertes import detecter_alertes
#from pea_trading.portfolios.portfolio import Portfolio
#from pea_trading.portfolios.stock import Stock, StockPriceHistory
#from pea_trading.users.models import User
#from pea_trading.services.yahoo_finance import update_stock_prices, update_historical_prices
#from pea_trading.services.live_scraper import  get_stock_prices, get_stock_info
from sqlalchemy import and_, func
from flask import current_app
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



### 🔁 JOB 1 : Alertes
def job_alertes(app, mail):
    from pea_trading.portfolios.portfolio import Portfolio
    from pea_trading.users.models import User
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
def job_update_stocks(app):
    from pea_trading.services.yahoo_finance import update_stock_prices, update_historical_prices
    from pea_trading.portfolios.stock import Stock, StockPriceHistory
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

def job_scraping_intraday(app, db):
    from pea_trading.portfolios.stock import Stock, StockPriceHistory
    from pea_trading.services.live_scraper import get_stock_prices, get_stock_info, intraday_logger
    
    if is_today_closed():
        print("📅 Aujourd'hui est un jour férié. Pas de scraping.")
        intraday_logger.info("📅 Jour férié détecté - Pas de scraping")
        return
    
    # 📊 LOG: Début du scraping
    start_time = datetime.now()
    intraday_logger.info("=" * 80)
    intraday_logger.info(f"🚀 DÉBUT DU SCRAPING INTRADAY - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    intraday_logger.info("=" * 80)
    
    print(f"[{start_time}] ⚡ Job scraping Boursorama en cours...")
    
    with app.app_context():
        today = datetime.now().date()
        updated = 0
        total_scraped = 0
        matched_isins = 0

        # Récupère toutes les lettres (A-Z)
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            stocks = get_stock_prices(letter)
            intraday_logger.info(f"📝 Lettre {letter}: {len(stocks)} actions trouvées sur Boursorama")

            for stock in stocks:
                total_scraped += 1
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
                        matched_isins += 1
                        print(f"✅ {isin} trouvé")
                        stock.current_price = price
                        stock.last_updated = datetime.now(paris_tz)
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
            
            # 📊 LOG: Fin du scraping avec statistiques
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            intraday_logger.info("=" * 80)
            intraday_logger.info(f"✅ FIN DU SCRAPING INTRADAY - {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            intraday_logger.info(f"⏱️  Durée: {duration:.2f} secondes")
            intraday_logger.info(f"📊 Total scrapé: {total_scraped} actions sur Boursorama")
            intraday_logger.info(f"🎯 ISINs matchés: {matched_isins}/{total_scraped} ({(matched_isins/total_scraped*100 if total_scraped > 0 else 0):.1f}%)")
            intraday_logger.info(f"💾 Valeurs mises à jour en base: {updated}")
            intraday_logger.info("=" * 80)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Commit final échoué : {e}")
            intraday_logger.error(f"❌ ERREUR lors du commit final: {e}")
            print(f"❌ Commit final échoué : {e}")
        print(f"✅ Scraping terminé : {updated} valeurs mises à jour (cours + historique).")
        #stocks = Stock.query.all()
        #for s in stocks:
        #    print(f"Stock en base : {s.name} -{s.isin}-")
        #    print(f"isin (en base): -{s.isin}- (len={len(s.isin)})")
      

paris_tz = pytz.timezone('Europe/Paris')

def register_jobs(scheduler, app, mail, db):
    print("📅 Enregistrement des jobs...") 
    scheduler.add_job(
        func=job_alertes,
        trigger=CronTrigger(day_of_week='mon-fri', hour='9-18', minute='*/50', timezone=paris_tz),
        kwargs={"app": app, "mail": mail},
        id="job_alertes", name="Alertes par email", misfire_grace_time=300
    )
    print("📌 Job job_alertes ajouté")
    scheduler.add_job(
        func=job_update_stocks,
        trigger=CronTrigger(day_of_week='sat', hour=8, timezone=paris_tz),
        kwargs={"app": app},
        id="job_update_stocks", name="Mise à jour hebdo des actions", misfire_grace_time=600
    )
    print("📌 job_update_stocks  ajouté")
    scheduler.add_job(
        func=job_scraping_intraday,
        trigger=CronTrigger(day_of_week='mon-fri', hour='9-18', minute='*/30', timezone=paris_tz),
        kwargs={"app": app, "db": db},
        id="job_scraping_intraday", name="Scraping intraday Yahoo", misfire_grace_time=300
    )
    print("📌 job_scraping_intraday  ajouté")

# === Wrappers pour lancement manuel (importations internes) ===

def run_alertes():
    """Wrapper sans argument pour exécuter job_alertes depuis l'interface admin"""
    from flask import current_app
    from flask_mail import Mail
    app = current_app._get_current_object()
    mail = Mail(app)
    job_alertes(app, mail)

def run_update_stocks():
    """Wrapper sans argument pour exécuter job_update_stocks depuis l'interface admin"""
    from flask import current_app
    app = current_app._get_current_object()
    job_update_stocks(app)

def run_scraping_intraday():
    """Wrapper sans argument pour exécuter job_scraping_intraday depuis l'interface admin"""
    from flask import current_app
    from pea_trading import db
    app = current_app._get_current_object()
    job_scraping_intraday(app, db)
