# manage.py
import os
import unittest
import click
import logging
from pea_trading import app, db
from pea_trading.services.yahoo_finance import update_stock_prices, update_historical_prices
from pea_trading.portfolios.portfolio import Portfolio
from pea_trading.services.export_utils import (
    export_portfolio_positions_to_csv,
    export_portfolio_transactions_to_csv,
    export_portfolio_cash_movements_to_csv
)
from pea_trading.services.import_utils import process_portfolio_transactions_csv
from pea_trading.services.import_utils import process_portfolio_positions_csv
from pea_trading.services.import_utils import process_portfolio_cash_movements_csv
from pea_trading.services.import_utils import process_stocks_csv_file, process_stock_history_csv_file
from pea_trading.services.export_utils import export_stocks_to_csv, export_stock_history_to_csv
from pea_trading.services.portfolio_loader import load_portfolio_data
from pea_trading.portfolios.stock import Stock
from pea_trading.users.models import User
from werkzeug.security import generate_password_hash
import csv
from datetime import datetime

# 📂 Configuration du logging pour manage.py
log_dir = os.path.join(os.path.dirname(__file__), 'pea_trading', 'static', 'logs')
os.makedirs(log_dir, exist_ok=True)

# 📄 Fichier de log pour les commandes manage.py
log_file = os.path.join(log_dir, 'manage.log')

# ⚙️ Configuration du logger pour manage.py
logger = logging.getLogger("manage")
logger.setLevel(logging.INFO)

# Handler pour fichier
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s | %(levelname)s | [MANAGE] %(message)s')
file_handler.setFormatter(formatter)

# Ajouter le handler s'il n'existe pas déjà
if not logger.handlers:
    logger.addHandler(file_handler)

@click.group()
def cli():
    pass


@cli.command("run")
@click.option("--env", default="dev", help="Environnement (dev, prod, test)")
@click.option("--host", default="127.0.0.1", help="Hôte à utiliser")
@click.option("--port", default=5000, help="Port à utiliser")
def run_server(env, host, port):
    """Lance le serveur Flask dans l’environnement spécifié"""
    logger.info(f"🚀 Commande 'run' exécutée - env: {env}, host: {host}, port: {port}")
    os.environ["FLASK_ENV"] = env
    debug = app.config["DEBUG"]
    print(f"🚀 Démarrage en mode {env.upper()} (debug={debug})")
    logger.info(f"Configuration: env={env.upper()}, debug={debug}")

     # 🔁 Démarrage des jobs de fond
    try:
        from app import launch_background_jobs
        launch_background_jobs()
        logger.info("✅ Jobs de fond lancés avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors du lancement des jobs de fond: {e}")

    # ✅ Lancer le serveur uniquement si ce n'est pas via `flask run`
    if os.environ.get("FLASK_RUN_FROM_CLI") != "true":
        print(f"🟢 Serveur Flask en cours d'exécution sur {host}:{port}...")
        logger.info(f"🟢 Serveur Flask démarré sur {host}:{port}")
        app.run(debug=debug, host=host, port=port)

# python manage.py  run --env="prod"

@cli.command("start_jobs")
def start_jobs():
    """
    🚀 Lance uniquement les jobs de fond définis dans app.py
    Usage : python manage.py start_jobs
    """
    logger.info("🚀 Commande 'start_jobs' exécutée")
    try:
        from app import launch_background_jobs
        print("🚀 Lancement des jobs de fond...")
        launch_background_jobs()
        print("✅ Jobs de fond lancés.")
        logger.info("✅ Jobs de fond lancés avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur lors du lancement des jobs: {e}")
        print(f"❌ Erreur: {e}")
# python manage.py start_jobs

@cli.command("update")
@click.option("--historique", is_flag=True, help="Inclure la mise à jour historique")
def update_data(historique):
    """Met à jour les prix des actions et éventuellement l’historique"""
    logger.info(f"🔁 Commande 'update' exécutée - historique: {historique}")
    
    with app.app_context():
        try:
            print("🔁 Mise à jour des prix actuels...")
            update_stock_prices()
            print("✅ Prix mis à jour.")
            logger.info("✅ Prix des actions mis à jour avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la mise à jour des prix: {e}")
            print(f"❌ Erreur prix: {e}")

        if historique:
            try:
                print("📈 Mise à jour des historiques...")
                update_historical_prices()
                print("✅ Historique mis à jour.")
                logger.info("✅ Historique des prix mis à jour avec succès")
            except Exception as e:
                logger.error(f"❌ Erreur lors de la mise à jour de l'historique: {e}")
                print(f"❌ Erreur historique: {e}")

@cli.command("scrape_intraday")
def scrape_intraday():
    """
    🔍 Lance manuellement le scraping intraday depuis Boursorama
    Usage : python manage.py scrape_intraday
    """
    logger.info("🔍 Commande 'scrape_intraday' exécutée")
    
    with app.app_context():
        try:
            from pea_trading.services.scheduler_jobs import job_scraping_intraday
            print("🔁 Scraping intraday en cours...")
            logger.info("🔁 Début du scraping intraday manuel")
            job_scraping_intraday(app, db)
            print("✅ Scraping intraday terminé.")
            logger.info("✅ Scraping intraday terminé avec succès")
        except Exception as e:
            error_msg = f"❌ Erreur lors du scraping intraday: {e}"
            logger.error(error_msg)
            print(error_msg)

@cli.command("init-db")
@click.option("--force", is_flag=True, help="Recharge le portefeuille même si non vide")
def init_db(force):
    """Initialise le portefeuille à partir des données de base"""
    logger.info(f"🛠 Commande 'init-db' exécutée - force: {force}")
    
    with app.app_context():
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)

            if not inspector.has_table("portfolios"):
                error_msg = "🚧 La table portfolios n'existe pas encore."
                print(error_msg)
                logger.warning(error_msg)
                return

            if force or not db.session.query(db.models['Portfolio']).first():
                print("🔄 Initialisation du portefeuille...")
                logger.info("🔄 Début de l'initialisation du portefeuille")
                load_portfolio_data()
                print("✅ Portefeuille chargé.")
                logger.info("✅ Portefeuille initialisé avec succès")
            else:
                info_msg = "ℹ️ Portefeuille déjà initialisé. Utilise --force pour forcer."
                print(info_msg)
                logger.info(info_msg)
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation: {e}")
            print(f"❌ Erreur: {e}")
# manage.py




@cli.command("change_password")
@click.argument("email")
def change_password(email):
    """
    🔐 Change le mot de passe d'un utilisateur via la CLI
    Usage : python manage.py change_password user@example.com
    """
    logger.info(f"🔐 Commande 'change_password' exécutée pour l'utilisateur: {email}")
    
    with app.app_context():
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                error_msg = f"❌ Utilisateur {email} introuvable."
                print(error_msg)
                logger.error(error_msg)
                return

            import getpass
            password = getpass.getpass("Nouveau mot de passe : ")
            confirm = getpass.getpass("Confirmez le mot de passe : ")
            
            if password != confirm:
                error_msg = "❌ Les mots de passe ne correspondent pas."
                print(error_msg)
                logger.warning(f"Tentative de changement de mot de passe échouée pour {email}: mots de passe non correspondants")
                return
            
            if not password:
                error_msg = "❌ Mot de passe vide."
                print(error_msg)
                logger.warning(f"Tentative de changement de mot de passe échouée pour {email}: mot de passe vide")
                return

            user.password_hash = generate_password_hash(password)
            db.session.commit()
            
            success_msg = "✅ Mot de passe mis à jour avec succès."
            print(success_msg)
            logger.info(f"✅ Mot de passe mis à jour avec succès pour l'utilisateur {email}")
            
        except Exception as e:
            error_msg = f"❌ Erreur lors du changement de mot de passe: {e}"
            logger.error(error_msg)
            print(error_msg)



    # python manage.py change_password user@example.com



@cli.command("list_stock_duplicates")
def list_stock_duplicates():
    """
    🔍 Liste les doublons dans la table Stock (symbol ou ISIN en double)
    Usage : python manage.py list_stock_duplicates
    """
    logger.info("🔍 Commande 'list_stock_duplicates' exécutée")
    
    with app.app_context():
        duplicates = {}

        # Doublons sur symbol
        symbols = db.session.query(Stock.symbol, db.func.count(Stock.id))\
            .group_by(Stock.symbol).having(db.func.count(Stock.id) > 1).all()
        if symbols:
            duplicates['symbol'] = symbols

        # Doublons sur ISIN
        isins = db.session.query(Stock.isin, db.func.count(Stock.id))\
            .group_by(Stock.isin).having(db.func.count(Stock.id) > 1).all()
        if isins:
            duplicates['isin'] = isins

        if not duplicates:
            print("✅ Aucun doublon détecté.")
            logger.info("✅ Aucun doublon détecté dans Stock")
            return

        print("⚠️ Doublons détectés :")
        logger.warning(f"⚠️ Doublons détectés: {len(duplicates)} type(s)")
        for field, values in duplicates.items():
            print(f"\nChamp : {field}")
            logger.warning(f"Doublons sur {field}: {len(values)} entrée(s)")
            for value, count in values:
                print(f" - {value} apparaît {count} fois")


    # python manage.py list_stock_duplicates

@cli.command("list_history_duplicates")
def list_history_duplicates():
    """
    🔍 Liste les doublons dans StockPriceHistory (même stock_id + date)
    Usage : python manage.py list_history_duplicates
    """
    logger.info("🔍 Commande 'list_history_duplicates' exécutée")
    from pea_trading.portfolios.stock import StockPriceHistory

    with app.app_context():
        doublons = db.session.query(
            StockPriceHistory.stock_id,
            StockPriceHistory.date,
            db.func.count(StockPriceHistory.id)
        ).group_by(
            StockPriceHistory.stock_id,
            StockPriceHistory.date
        ).having(
            db.func.count(StockPriceHistory.id) > 1
        ).all()

        if not doublons:
            print("✅ Aucun doublon dans StockPriceHistory.")
            logger.info("✅ Aucun doublon dans StockPriceHistory")
            return

        print("⚠️ Doublons détectés dans StockPriceHistory :\n")
        logger.warning(f"⚠️ {len(doublons)} doublon(s) détecté(s) dans StockPriceHistory")
        for stock_id, date, count in doublons:
            print(f"- stock_id = {stock_id}, date = {date.strftime('%Y-%m-%d')} ➜ {count} entrées")

    # python manage.py list_history_duplicates

@cli.command("delete_history_duplicates")
def delete_history_duplicates():
    """
    🗑️ Supprime les doublons dans StockPriceHistory (garde le plus récent ID)
    Usage : python manage.py delete_history_duplicates
    """
    logger.info("🗑️ Commande 'delete_history_duplicates' exécutée")
    from pea_trading.portfolios.stock import StockPriceHistory

    with app.app_context():
        print("🔍 Recherche des doublons...")
        logger.info("🔍 Recherche des doublons dans StockPriceHistory")
        
        doublons = db.session.query(
            StockPriceHistory.stock_id,
            StockPriceHistory.date,
            db.func.count(StockPriceHistory.id)
        ).group_by(
            StockPriceHistory.stock_id,
            StockPriceHistory.date
        ).having(
            db.func.count(StockPriceHistory.id) > 1
        ).all()

        if not doublons:
            print("✅ Aucun doublon trouvé.")
            logger.info("✅ Aucun doublon trouvé dans StockPriceHistory")
            return

        total_suppr = 0

        for stock_id, date, count in doublons:
            entries = StockPriceHistory.query.filter_by(stock_id=stock_id, date=date).order_by(StockPriceHistory.id.desc()).all()
            to_delete = entries[1:]  # Conserver la plus récente (id le plus haut)
            for entry in to_delete:
                db.session.delete(entry)
                total_suppr += 1

        db.session.commit()
        print(f"🗑️ {total_suppr} doublon(s) supprimé(s) de StockPriceHistory.")
        logger.info(f"🗑️ {total_suppr} doublon(s) supprimé(s) de StockPriceHistory")

    # python manage.py delete_history_duplicates


@cli.command("export_all_stocks_csv")
def export_all_stocks_csv():
    """Exporte toutes les actions vers un fichier CSV"""
    logger.info("📤 Commande 'export_all_stocks_csv' exécutée")
    
    with app.app_context():
        try:
            filepath = export_stocks_to_csv()
            print(f"✅ Export des actions terminé : {filepath}")
            logger.info(f"✅ Export des actions terminé : {filepath}")
        except Exception as e:
            error_msg = f"❌ Erreur lors de l'export des actions: {e}"
            logger.error(error_msg)
            print(error_msg)


    # python manage.py export_all_stocks_csv


@cli.command("export_all_stock_history_csv")
def export_all_stock_history_csv():
    """Exporte l'historique de toutes les actions vers un fichier CSV"""
    logger.info("📤 Commande 'export_all_stock_history_csv' exécutée")
    
    with app.app_context():
        try:
            filepath = export_stock_history_to_csv()
            print(f"✅ Export de l'historique terminé : {filepath}")
            logger.info(f"✅ Export de l'historique terminé : {filepath}")
        except Exception as e:
            error_msg = f"❌ Erreur lors de l'export de l'historique: {e}"
            logger.error(error_msg)
            print(error_msg)

    # python manage.py export_all_stock_history_csv

@cli.command("import_stocks_csv")
def import_stocks_csv():
    """Importe les actions depuis un fichier CSV"""
    logger.info("📥 Commande 'import_stocks_csv' exécutée")
    
    with app.app_context():
        success, error = process_stocks_csv_file()
        if success:
            print(f"✅ Importation des actions réussie ")
            logger.info("✅ Importation des actions réussie")
        else:
            print(f"❌ Erreur : {error}")
            logger.error(f"❌ Erreur lors de l'importation des actions: {error}")

    # python manage.py import_stocks_csv

@cli.command("import_all_stock_history_csv")
def import_all_stock_history_csv():
    """Importe tout l'historique des valeurs depuis un fichier CSV"""
    logger.info("📥 Commande 'import_all_stock_history_csv' exécutée")
    
    with app.app_context():
        try:
            success, result = process_stock_history_csv_file()
            if success:
                print(f"✅ {result} lignes importées ")
                logger.info(f"✅ {result} lignes d'historique importées")
            else:
                print(f"❌ Erreur pendant l'import : {result}")
                logger.error(f"❌ Erreur pendant l'import de l'historique: {result}")
        except Exception as e:
            error_msg = f"❌ Erreur lors de l'import : {str(e)}"
            print(error_msg)
            logger.error(error_msg)

    # python manage.py import_all_stock_history_csv

@cli.command("export_portfolio_csv")
@click.argument("portfolio_name")
@click.option("--output", default=None, help="Nom du fichier de sortie (par défaut : portfolio_export_<nom>_<timestamp>.csv)")
def export_portfolio_csv(portfolio_name, output):
    """
    📁 Exporte les positions d'un portefeuille (symbole, ISIN, nom, quantité, prix d'achat, secteur) vers un CSV.
    Usage : python manage.py export_portfolio_csv "PEA"
    """
    logger.info(f"📁 Commande 'export_portfolio_csv' exécutée - portfolio: {portfolio_name}, output: {output}")

    with app.app_context():
        try:
            portfolio = Portfolio.query.filter_by(name=portfolio_name).first()
            if not portfolio:
                error_msg = f"❌ Portefeuille '{portfolio_name}' introuvable."
                print(error_msg)
                logger.error(error_msg)
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = portfolio_name.replace(" ", "_")
            filename = output or f"portefeuille_export_{safe_name}_{timestamp}.csv"
            path = export_portfolio_positions_to_csv(portfolio, filename)
            print(f"✅ Export effectué : {path}")
            logger.info(f"✅ Export du portefeuille '{portfolio_name}' effectué : {path}")
        except Exception as e:
            error_msg = f"❌ Erreur lors de l'export du portefeuille: {e}"
            logger.error(error_msg)
            print(error_msg)


    # python manage.py export_portfolio_csv "PEA"

@cli.command("export_transactions_csv")
@click.argument("portfolio_name")
@click.option("--output", default=None, help="Nom du fichier de sortie (par défaut : transactions_<nom>_<timestamp>.csv)")
def export_transactions_csv(portfolio_name, output):
    """
    📄 Exporte les transactions d'un portefeuille vers un fichier CSV.
    Usage : python manage.py export_transactions_csv "PEA"
    """
    

    logger.info(f"📄 Commande 'export_transactions_csv' exécutée - portfolio: {portfolio_name}, output: {output}")
    
    with app.app_context():
        try:
            portfolio = Portfolio.query.filter_by(name=portfolio_name).first()
            if not portfolio:
                error_msg = f"❌ Portefeuille '{portfolio_name}' introuvable."
                print(error_msg)
                logger.error(error_msg)
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = portfolio_name.replace(" ", "_")
            filename = output or f"transactions_{safe_name}_{timestamp}.csv"
            
            logger.info(f"📄 Début de l'export des transactions pour le portefeuille '{portfolio_name}'")
            path = export_portfolio_transactions_to_csv(portfolio, filename)
            
            success_msg = f"✅ Export des transactions du portefeuille '{portfolio_name}' terminé : {path}"
            print(success_msg)
            logger.info(success_msg)
            
        except Exception as e:
            error_msg = f"❌ Erreur lors de l'export des transactions: {e}"
            logger.error(error_msg)
            print(error_msg)

    # python manage.py export_transactions_csv "PEA"
    # python manage.py export_transactions_csv "PEA-PME" --output "transactions_export_PEA-PME.csv"

@cli.command("export_cash_mouvements_csv")
@click.argument("portfolio_name")
@click.option("--output", default=None, help="Nom du fichier de sortie (par défaut : cash_movements_<nom>_<timestamp>.csv)")
def export_cash_movements_csv(portfolio_name, output):
    """
    💰 Exporte les mouvements de trésorerie d'un portefeuille vers un CSV.
    Usage : python manage.py export_cash_movements_csv "PEA"
    """
    logger.info(f"💰 Commande 'export_cash_mouvements_csv' exécutée - portfolio: {portfolio_name}, output: {output}")

    with app.app_context():
        try:
            portfolio = Portfolio.query.filter_by(name=portfolio_name).first()
            if not portfolio:
                error_msg = f"❌ Portefeuille '{portfolio_name}' introuvable."
                print(error_msg)
                logger.error(error_msg)
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = portfolio_name.replace(" ", "_")
            filename = output or f"cash_mouvements_{safe_name}_{timestamp}.csv"
            path = export_portfolio_cash_movements_to_csv(portfolio, filename)

            print(f"✅ Export des mouvements de trésorerie pour '{portfolio_name}' terminé : {path}")
            logger.info(f"✅ Export des mouvements de trésorerie pour '{portfolio_name}' terminé : {path}")
        except Exception as e:
            error_msg = f"❌ Erreur lors de l'export des mouvements de trésorerie: {e}"
            logger.error(error_msg)
            print(error_msg)

    # python manage.py export_cash_mouvements_csv "PEA"
    # python manage.py export_cash_mouvements_csv "PEA-PME" --output "cash_mouvements_export_PEA-PME.csv"

@cli.command("import_portfolio_positions_csv")
@click.argument("portfolio_name")
@click.argument("filename")
def import_portfolio_positions_csv(portfolio_name, filename):
    """Importe les positions d'un portefeuille depuis un fichier CSV"""
    logger.info(f"📥 Commande 'import_portfolio_positions_csv' exécutée - portfolio: {portfolio_name}, file: {filename}")
    
    with app.app_context():
        success, message = process_portfolio_positions_csv(portfolio_name, filename)
        if success:
            print(f"✅ {message}")
            logger.info(f"✅ Import des positions réussi pour '{portfolio_name}': {message}")
        else:
            print(f"❌ Erreur : {message}")
            logger.error(f"❌ Erreur lors de l'import des positions pour '{portfolio_name}': {message}")
    # python manage.py import_portfolio_positions_csv "PEA" portefeuille_export_PEA_20250531_214843.csv         

@cli.command("import_transactions_csv")
@click.argument("portfolio_name")
@click.argument("filename")
def import_transactions_csv(portfolio_name, filename):
    """Importe les transactions d'un portefeuille depuis un fichier CSV"""
    logger.info(f"📥 Commande 'import_transactions_csv' exécutée - portfolio: {portfolio_name}, file: {filename}")
    
    with app.app_context():
        success, message = process_portfolio_transactions_csv(portfolio_name, filename)
        if success:
            print(f"✅ {message}")
            logger.info(f"✅ Import des transactions réussi pour '{portfolio_name}': {message}")
        else:
            print(f"❌ Erreur : {message}")
            logger.error(f"❌ Erreur lors de l'import des transactions pour '{portfolio_name}': {message}")

    # python manage.py import_transactions_csv "PEA-PME" transactions_PEA-PME_20250531_223800.csv        

@cli.command("import_cash_movements_csv")
@click.argument("portfolio_name")
@click.argument("filename")
def import_cash_movements_csv(portfolio_name, filename):
    """Importe les mouvements de trésorerie d'un portefeuille depuis un fichier CSV"""
    logger.info(f"📥 Commande 'import_cash_movements_csv' exécutée - portfolio: {portfolio_name}, file: {filename}")
    
    with app.app_context():
        success, message = process_portfolio_cash_movements_csv(portfolio_name, filename)
        if success:
            print(f"✅ {message}")
            logger.info(f"✅ Import des mouvements de trésorerie réussi pour '{portfolio_name}': {message}")
        else:
            print(f"❌ Erreur : {message}")
            logger.error(f"❌ Erreur lors de l'import des mouvements de trésorerie pour '{portfolio_name}': {message}")

    
    # python manage.py import_cash_movements_csv "PEA-PME" cash_mouvements_PEA-PME_20250531_223806.csv

@cli.command("show_logs")
@click.option("--lines", default=50, help="Nombre de lignes à afficher (défaut: 50)")
@click.option("--type", "log_type", default="manage", help="Type de log: 'manage', 'scheduler', 'intraday', 'yfinance' ou 'all'")
def show_logs(lines, log_type):
    """
    📄 Affiche les logs récents
    Usage : python manage.py show_logs --lines=20 --type=yfinance
    """
    logger.info(f"📄 Commande 'show_logs' exécutée - lines: {lines}, type: {log_type}")
    
    # Deux emplacements possibles pour les logs
    log_dir_static = os.path.join(os.path.dirname(__file__), 'pea_trading', 'static', 'logs')
    log_dir_local = os.path.join(os.path.dirname(__file__), 'logs_local')
    
    if log_type == "manage":
        log_files = [os.path.join(log_dir_static, 'manage.log')]
    elif log_type == "scheduler":
        log_files = [os.path.join(log_dir_static, 'scheduler.log')]
    elif log_type == "intraday":
        log_files = [os.path.join(log_dir_local, 'intraday.log')]
    elif log_type == "yfinance":
        log_files = [os.path.join(log_dir_local, 'yfinance.log')]
    elif log_type == "all":
        log_files = [
            os.path.join(log_dir_static, 'manage.log'),
            os.path.join(log_dir_static, 'scheduler.log'),
            os.path.join(log_dir_local, 'intraday.log'),
            os.path.join(log_dir_local, 'yfinance.log')
        ]
    else:
        print(f"❌ Type de log invalide: {log_type}. Utilisez 'manage', 'scheduler', 'intraday', 'yfinance' ou 'all'")
        return
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n📄 === {os.path.basename(log_file)} (dernières {lines} lignes) ===")
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    for line in recent_lines:
                        print(line.strip())
            except Exception as e:
                print(f"❌ Erreur lors de la lecture de {log_file}: {e}")
        else:
            print(f"⚠️ Fichier de log introuvable: {log_file}")

@cli.command("test")
def run_tests():
    """Lance tous les tests unitaires"""
    logger.info("🧪 Commande 'test' exécutée")
    
    try:
        
        # Définir le chemin du dossier tests dans le projet
        tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
        
        # Vérifier si le dossier tests existe
        if not os.path.exists(tests_dir):
            print(f"⚠️ Aucun dossier 'tests' trouvé dans le projet.")
            print(f"📁 Créez un dossier 'tests/' avec vos fichiers de test.")
            logger.warning("Aucun dossier de tests trouvé")
            return
        
        # Découvrir les tests uniquement dans le dossier du projet
        tests = unittest.TestLoader().discover(tests_dir, pattern='test*.py')
        result = unittest.TextTestRunner(verbosity=2).run(tests)
        
        if result.wasSuccessful():
            logger.info("✅ Tous les tests ont réussi")
        else:
            logger.warning(f"⚠️ Tests échoués: {len(result.failures)} failures, {len(result.errors)} errors")
            exit(1)
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution des tests: {e}")
        print(f"❌ Erreur: {e}")
        exit(1)


@cli.command("show_scheduler")
def show_scheduler():
    """
    📅 Affiche les tâches planifiées (scheduler jobs)
    Usage : python manage.py show_scheduler
    """
    logger.info("📅 Commande 'show_scheduler' exécutée")
    
    with app.app_context():
        try:
            from pea_trading.services.scheduler_utils import scheduler_instance
            
            if not scheduler_instance.running:
                print("⚠️ Le scheduler n'est pas en cours d'exécution.")
                logger.warning("Le scheduler n'est pas en cours d'exécution")
                return
            
            jobs = scheduler_instance.get_jobs()
            
            if not jobs:
                print("ℹ️ Aucune tâche planifiée trouvée.")
                logger.info("Aucune tâche planifiée trouvée")
                return
            
            print(f"📅 === Tâches planifiées ({len(jobs)} job(s)) ===\n")
            
            for job in jobs:
                print(f"🔹 Job ID: {job.id}")
                print(f"   Nom: {job.name}")
                print(f"   Fonction: {job.func.__name__ if hasattr(job.func, '__name__') else job.func}")
                
                # Afficher le déclencheur
                if hasattr(job.trigger, 'fields'):
                    fields = job.trigger.fields
                    trigger_info = []
                    for field in fields:
                        if str(field) != '*':
                            trigger_info.append(f"{field.name}={field}")
                    if trigger_info:
                        print(f"   Déclencheur: {', '.join(trigger_info)}")
                    else:
                        print(f"   Déclencheur: {job.trigger}")
                else:
                    print(f"   Déclencheur: {job.trigger}")
                
                # Prochaine exécution
                next_run = job.next_run_time
                if next_run:
                    print(f"   Prochaine exécution: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                else:
                    print(f"   Prochaine exécution: Non planifiée")
                
                print()
            
            logger.info(f"Affichage de {len(jobs)} job(s) planifiés")
            
        except Exception as e:
            error_msg = f"❌ Erreur lors de l'affichage du scheduler: {e}"
            logger.error(error_msg)
            print(error_msg)

@cli.command("show_cron")
def show_cron():
    """
    ⏰ Affiche les tâches cron configurées
    Usage : python manage.py show_cron
    """
    logger.info("⏰ Commande 'show_cron' exécutée")
    
    try:
        cron_file = os.path.join(os.path.dirname(__file__), 'cron_jobs.txt')
        
        if not os.path.exists(cron_file):
            print(f"⚠️ Fichier cron_jobs.txt introuvable.")
            logger.warning("Fichier cron_jobs.txt introuvable")
            return
        
        print("⏰ === Tâches CRON configurées ===\n")
        
        with open(cron_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Parser la ligne cron
                parts = line.split()
                if len(parts) >= 6:
                    minute, hour, day, month, weekday = parts[0:5]
                    command = ' '.join(parts[6:])
                    
                    print(f"🔹 Planification: {minute} {hour} {day} {month} {weekday}")
                    print(f"   Commande: {command}")
                    
                    # Explication lisible
                    explanation = []
                    if minute == '*':
                        explanation.append("chaque minute")
                    else:
                        explanation.append(f"à la minute {minute}")
                    
                    if hour == '*':
                        explanation.append("de chaque heure")
                    else:
                        explanation.append(f"à {hour}h")
                    
                    if weekday != '*':
                        days = {0: 'dimanche', 1: 'lundi', 2: 'mardi', 3: 'mercredi', 
                               4: 'jeudi', 5: 'vendredi', 6: 'samedi'}
                        explanation.append(f"le {days.get(int(weekday), weekday)}")
                    
                    if day != '*':
                        explanation.append(f"le jour {day}")
                    
                    if month != '*':
                        explanation.append(f"du mois {month}")
                    
                    print(f"   📝 {' '.join(explanation)}")
                    print()
            elif line.startswith('#'):
                print(f"💬 {line}")
        
        logger.info("Affichage des tâches cron terminé")
        
    except Exception as e:
        error_msg = f"❌ Erreur lors de l'affichage des tâches cron: {e}"
        logger.error(error_msg)
        print(error_msg)

@cli.command("shell")
def interactive_shell():
    """Shell Python avec le contexte Flask"""
    logger.info("🔧 Commande 'shell' exécutée")
    import code
    banner = "🔧 Shell interactif - `app`, `db` disponibles"
    context = {'app': app, 'db': db}
    code.interact(banner=banner, local=context)

# docker exec -it flaskfolio-test  python manage.py  shell
# python manage.py  shell   
# 
#  Shell interactif - `app`, `db` disponibles
#>>> from tasks_scheduler import scheduler
#>>> scheduler.get_jobs()
#[]       

if __name__ == '__main__':
    cli()
