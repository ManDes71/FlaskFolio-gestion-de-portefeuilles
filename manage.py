# manage.py
import os
import click
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



@click.group()
def cli():
    pass


@cli.command("run")
@click.option("--env", default="dev", help="Environnement (dev, prod, test)")
@click.option("--host", default="127.0.0.1", help="Hôte à utiliser")
@click.option("--port", default=5000, help="Port à utiliser")
def run_server(env, host, port):
    """Lance le serveur Flask dans l’environnement spécifié"""
    os.environ["FLASK_ENV"] = env
    debug = app.config["DEBUG"]
    print(f"🚀 Démarrage en mode {env.upper()} (debug={debug})")

    # 🔁 Démarrage des jobs de fond

    from app import launch_background_jobs

    launch_background_jobs()
    # ✅ Lancer le serveur uniquement si ce n’est pas via `flask run`
    if os.environ.get("FLASK_RUN_FROM_CLI") != "true":
        print(f"🟢 Serveur Flask en cours d’exécution sur {host}:{port}...")
        app.run(debug=debug, host=host, port=port)

@cli.command("update")
@click.option("--historique", is_flag=True, help="Inclure la mise à jour historique")
def update_data(historique):
    """Met à jour les prix des actions et éventuellement l’historique"""
    with app.app_context():
        print("🔁 Mise à jour des prix actuels...")
        update_stock_prices()
        print("✅ Prix mis à jour.")

        if historique:
            print("📈 Mise à jour des historiques...")
            update_historical_prices()
            print("✅ Historique mis à jour.")


@cli.command("init-db")
@click.option("--force", is_flag=True, help="Recharge le portefeuille même si non vide")
def init_db(force):
    """Initialise le portefeuille à partir des données de base"""
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)

        if not inspector.has_table("portfolios"):
            print("🚧 La table portfolios n’existe pas encore.")
            return

        if force or not db.session.query(db.models['Portfolio']).first():
            print("🔄 Initialisation du portefeuille...")
            load_portfolio_data()
            print("✅ Portefeuille chargé.")
        else:
            print("ℹ️ Portefeuille déjà initialisé. Utilise --force pour forcer.")

# manage.py




@cli.command("change_password")
@click.argument("email")
def change_password(email):
    """
    🔐 Change le mot de passe d'un utilisateur via la CLI
    Usage : python manage.py change_password user@example.com
    """
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print("❌ Utilisateur introuvable.")
            return

        import getpass
        password = getpass.getpass("Nouveau mot de passe : ")
        confirm = getpass.getpass("Confirmez le mot de passe : ")
        if password != confirm:
            print("❌ Les mots de passe ne correspondent pas.")
            return
        
        if not password:
            print("❌ Mot de passe vide.")
            return

        user.password_hash = generate_password_hash(password)
        db.session.commit()
        print("✅ Mot de passe mis à jour avec succès.")


    # python manage.py change_password user@example.com



@cli.command("list_stock_duplicates")
def list_stock_duplicates():
    """
    🔍 Liste les doublons dans la table Stock (symbol ou ISIN en double)
    Usage : python manage.py list_stock_duplicates
    """
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
            return

        print("⚠️ Doublons détectés :")
        for field, values in duplicates.items():
            print(f"\nChamp : {field}")
            for value, count in values:
                print(f" - {value} apparaît {count} fois")


    # python manage.py list_stock_duplicates

@cli.command("list_history_duplicates")
def list_history_duplicates():
    """
    🔍 Liste les doublons dans StockPriceHistory (même stock_id + date)
    Usage : python manage.py list_history_duplicates
    """
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
            return

        print("⚠️ Doublons détectés dans StockPriceHistory :\n")
        for stock_id, date, count in doublons:
            print(f"- stock_id = {stock_id}, date = {date.strftime('%Y-%m-%d')} ➜ {count} entrées")

    # python manage.py list_history_duplicates

@cli.command("delete_history_duplicates")
def delete_history_duplicates():
    """
    🗑️ Supprime les doublons dans StockPriceHistory (garde le plus récent ID)
    Usage : python manage.py delete_history_duplicates
    """
    from pea_trading.portfolios.stock import StockPriceHistory

    with app.app_context():
        print("🔍 Recherche des doublons...")
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

    # python manage.py delete_history_duplicates


@cli.command("export_all_stocks_csv")
def export_all_stocks_csv():
    with app.app_context():
        filepath = export_stocks_to_csv()
        print(f"✅ Export des actions terminé : {filepath}")


    # python manage.py export_all_stocks_csv


@cli.command("export_all_stock_history_csv")
def export_all_stock_history_csv():
    with app.app_context():
        filepath=export_stock_history_to_csv()
        print(f"✅ Export de l’historique terminé : {filepath}")

    # python manage.py export_all_stock_history_csv

@cli.command("import_stocks_csv")
def import_stocks_csv():
    with app.app_context():
        success, error = process_stocks_csv_file()
        if success:
            print(f"✅ Importation des actions réussie ")
        else:
            print(f"❌ Erreur : {error}")

    # python manage.py import_stocks_csv

@cli.command("import_all_stock_history_csv")
def import_all_stock_history_csv():
    """Importe tout l’historique des valeurs depuis un fichier CSV"""
    with app.app_context():
        try:
            success, result = process_stock_history_csv_file()
            if success:
                print(f"✅ {result} lignes importées ")
            else:
                print(f"❌ Erreur pendant l'import : {result}")
        except Exception as e:
            print(f"❌ Erreur lors de l'import : {str(e)}")

    # python manage.py import_all_stock_history_csv

@cli.command("export_portfolio_csv")
@click.argument("portfolio_name")
@click.option("--output", default=None, help="Nom du fichier de sortie (par défaut : portfolio_export_<nom>_<timestamp>.csv)")
def export_portfolio_csv(portfolio_name, output):
    """
    📁 Exporte les positions d'un portefeuille (symbole, ISIN, nom, quantité, prix d'achat, secteur) vers un CSV.
    Usage : python manage.py export_portfolio_csv "PEA"
    """
   

    with app.app_context():
        portfolio = Portfolio.query.filter_by(name=portfolio_name).first()
        if not portfolio:
            print(f"❌ Portefeuille '{portfolio_name}' introuvable.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = portfolio_name.replace(" ", "_")
        filename = output or f"portefeuille_export_{safe_name}_{timestamp}.csv"
        path = export_portfolio_positions_to_csv(portfolio, filename)
        print(f"✅ Export effectué : {path}")


    # python manage.py export_portfolio_csv "PEA"

@cli.command("export_transactions_csv")
@click.argument("portfolio_name")
@click.option("--output", default=None, help="Nom du fichier de sortie (par défaut : transactions_<nom>_<timestamp>.csv)")
def export_transactions_csv(portfolio_name, output):
    """
    📄 Exporte les transactions d'un portefeuille vers un fichier CSV.
    Usage : python manage.py export_transactions_csv "PEA"
    """
    

    with app.app_context():
        portfolio = Portfolio.query.filter_by(name=portfolio_name).first()
        if not portfolio:
            print(f"❌ Portefeuille '{portfolio_name}' introuvable.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = portfolio_name.replace(" ", "_")
        filename = output or f"transactions_{safe_name}_{timestamp}.csv"
        path = export_portfolio_transactions_to_csv(portfolio, filename)
        print(f"✅ Export des transactions du portefeuille '{portfolio_name}' terminé : {path}")

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
    

    with app.app_context():
        portfolio = Portfolio.query.filter_by(name=portfolio_name).first()
        if not portfolio:
            print(f"❌ Portefeuille '{portfolio_name}' introuvable.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = portfolio_name.replace(" ", "_")
        filename = output or f"cash_mouvements_{safe_name}_{timestamp}.csv"
        path = export_portfolio_cash_movements_to_csv(portfolio, filename)

        print(f"✅ Export des mouvements de trésorerie pour '{portfolio_name}' terminé : {path}")

    # python manage.py export_cash_mouvements_csv "PEA"
    # python manage.py export_cash_mouvements_csv "PEA-PME" --output "cash_mouvements_export_PEA-PME.csv"

@cli.command("import_portfolio_positions_csv")
@click.argument("portfolio_name")
@click.argument("filename")
def import_portfolio_positions_csv(portfolio_name, filename):
    with app.app_context():
        success, message = process_portfolio_positions_csv(portfolio_name, filename)
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ Erreur : {message}")
    # python manage.py import_portfolio_positions_csv "PEA" portefeuille_export_PEA_20250531_214843.csv         

@cli.command("import_transactions_csv")
@click.argument("portfolio_name")
@click.argument("filename")
def import_transactions_csv(portfolio_name, filename):
    with app.app_context():
        success, message = process_portfolio_transactions_csv(portfolio_name, filename)
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ Erreur : {message}")

    # python manage.py import_transactions_csv "PEA-PME" transactions_PEA-PME_20250531_223800.csv        

@cli.command("import_cash_movements_csv")
@click.argument("portfolio_name")
@click.argument("filename")
def import_cash_movements_csv(portfolio_name, filename):
    with app.app_context():
        success, message = process_portfolio_cash_movements_csv(portfolio_name, filename)
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ Erreur : {message}")

    
    # python manage.py import_cash_movements_csv "PEA-PME" cash_mouvements_PEA-PME_20250531_223806.csv

@cli.command("test")
def run_tests():
    """Lance tous les tests unitaires"""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if not result.wasSuccessful():
        exit(1)


@cli.command("shell")
def interactive_shell():
    """Shell Python avec le contexte Flask"""
    import code
    banner = "🔧 Shell interactif - `app`, `db` disponibles"
    context = {'app': app, 'db': db}
    code.interact(banner=banner, local=context)


if __name__ == '__main__':
    cli()
