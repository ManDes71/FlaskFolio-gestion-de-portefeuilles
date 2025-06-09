# pea_trading\services\portfolio_loader.py
"""
Service pour charger les données du portefeuille
"""
from pea_trading import db
from pea_trading.portfolios.portfolio import Portfolio
from pea_trading.portfolios.stock import  Stock, Position
from config.stocks import  STOCKS_CONFIG
from datetime import datetime

PORTFOLIO_DATA = [
    {
        "name": "AIR LIQUIDE",
        "yahoo_symbol": "AI.PA",
        "isin": "FR0000120073",
        "quantity": 4.0,
        "buying_price": 115.04,
        "amount": 460.16,
        "ratio": 0.0383105589648423,
        "portfolio_type": "PEA"
    },
    {
        "name": "AIRBUS",
        "yahoo_symbol": "AIR.PA",
        "isin": "NL0000235190",
        "quantity": 5.0,
        "buying_price": 91.90,
        "amount": 459.50,
        "ratio": 0.03825561075353146,
        "portfolio_type": "PEA"
    },
    {
        "name": "ALSTOM",
        "yahoo_symbol": "ALO.PA",
        "isin": "FR0010220475",
        "quantity": 10.0,
        "buying_price": 43.93,
        "amount": 439.30,
        "ratio": 0.03657386246795728,
        "portfolio_type": "PEA"
    },
    {
        "name": "ARCURE",
        "yahoo_symbol": "ALCUR.PA",
        "isin": "FR0013398997",
        "quantity": 200.0,
        "buying_price": 2.56,
        "amount": 512.0,
        "ratio": 0.042626491198711876,
        "portfolio_type": "PEA"
    },
    {
        "name": "BNP PARIBAS ACT.A",
        "yahoo_symbol": "BNP.PA",
        "isin": "FR0000131104",
        "quantity": 7.0,
        "buying_price": 63.82,
        "amount": 446.74,
        "ratio": 0.03719327866818856,
        "portfolio_type": "PEA"
    },
    {
        "name": "BUREAU VERITAS",
        "yahoo_symbol": "BVI.PA",
        "isin": "FR0006174348",
        "quantity": 20.0,
        "buying_price": 20.96,
        "amount": 419.20,
        "ratio": 0.03490043966894535,
        "portfolio_type": "PEA"
    },
    {
        "name": "CARREFOUR",
        "yahoo_symbol": "CA.PA",
        "isin": "FR0000120172",
        "quantity": 30.0,
        "buying_price": 15.42,
        "amount": 462.60,
        "ratio": 0.038513700836961165,
        "portfolio_type": "PEA"
    },
    {
        "name": "GTT",
        "yahoo_symbol": "GTT.PA",
        "isin": "FR0011726835",
        "quantity": 6.0,
        "buying_price": 79.57,
        "amount": 477.42,
        "ratio": 0.03974753794548637,
        "portfolio_type": "PEA"
    },
    {
        "name": "LYXOR ETF BX4",
        "yahoo_symbol": "BX4.PA",
        "isin": "FR0010411884",
        "quantity": 200.0,
        "buying_price": 2.96,
        "amount": 592.0,
        "ratio": 0.04928688044851061,
        "portfolio_type": "PEA"
    },
    {
        "name": "LYXOR ETF SHT CAC",
        "yahoo_symbol": "SHC.PA",
        "isin": "FR0010591362",
        "quantity": 20.0,
        "buying_price": 19.43,
        "amount": 388.60,
        "ratio": 0.032352840780897334,
        "portfolio_type": "PEA"
    },
    {
        "name": "NEOEN",
        "yahoo_symbol": "NEOEN.PA",
        "isin": "FR0011675362",
        "quantity": 15.0,
        "buying_price": 33.39,
        "amount": 500.85,
        "ratio": 0.04169819944702118,
        "portfolio_type": "PEA"
    },
    {
        "name": "NEXANS",
        "yahoo_symbol": "NEX.PA",
        "isin": "FR0000044448",
        "quantity": 5.0,
        "buying_price": 92.27,
        "amount": 461.35,
        "ratio": 0.03840963225493305,
        "portfolio_type": "PEA"
    },
    {
        "name": "SARTORIUS STED BIO",
        "yahoo_symbol": "DIM.PA",
        "isin": "FR0013154002",
        "quantity": 2.0,
        "buying_price": 315.51,
        "amount": 631.02,
        "ratio": 0.05253548530509994,
        "portfolio_type": "PEA"
    },
    {
        "name": "SCHNEIDER ELECTRIC",
        "yahoo_symbol": "SU.PA",
        "isin": "FR0000121972",
        "quantity": 3.0,
        "buying_price": 153.12,
        "amount": 459.36,
        "ratio": 0.038243955072344314,
        "portfolio_type": "PEA"
    },
    {
        "name": "SOITEC",
        "yahoo_symbol": "SOI.PA",
        "isin": "FR0013227113",
        "quantity": 11.0,
        "buying_price": 149.44,
        "amount": 1643.84,
        "ratio": 0.1368576783048643,
        "portfolio_type": "PEA"
    },
    {
        "name": "STMICROELECTRONICS",
        "yahoo_symbol": "STMPA.PA",
        "isin": "NL0000226223",
        "quantity": 39.0,
        "buying_price": 35.83,
        "amount": 1397.37,
        "ratio": 0.11633785157489064,
        "portfolio_type": "PEA"
    },
    {
        "name": "TOTALENERGIES",
        "yahoo_symbol": "TTE.PA",
        "isin": "FR0000120271",
        "quantity": 25.0,
        "buying_price": 33.08,
        "amount": 827.0,
        "ratio": 0.06885177386979438,
        "portfolio_type": "PEA"
    },
    {
        "name": "VEOLIA ENVIRON.",
        "yahoo_symbol": "VIE.PA",
        "isin": "FR0000124141",
        "quantity": 50.0,
        "buying_price": 19.98,
        "amount": 999.0,
        "ratio": 0.08317161075686165,
        "portfolio_type": "PEA"
    },
    {
        "name": "VERIMATRIX",
        "yahoo_symbol": "VMX.PA",
        "isin": "FR0010291245",
        "quantity": 200.0,
        "buying_price": 2.17,
        "amount": 434.0,
        "ratio": 0.03613261168015811,
        "portfolio_type": "PEA"
    }
]

def load_portfolio_data():
    """
    Charge les données du portefeuille dans la base de données.
    Crée un nouveau portefeuille s'il n'existe pas déjà.
    """
    try:
        # Créer le portefeuille PEA s'il n'existe pas
        portfolio = Portfolio.query.filter_by(name="PEA").first()
        if not portfolio:
            portfolio = Portfolio(
                name="PEA",
                description="Plan d'Épargne en Actions",
                user_id=1  # ID utilisateur par défaut
            )
            db.session.add(portfolio)
            db.session.commit()

        # Charger chaque position
        for data in PORTFOLIO_DATA:
            # Vérifier si l'action existe déjà
            stock = Stock.query.filter_by(symbol=data["yahoo_symbol"]).first()
            if not stock:
                stock_config = next((conf for conf in STOCKS_CONFIG.values() if conf['yahoo_symbol'] == data["yahoo_symbol"]), None)
                print(stock_config)
                stock = Stock(
                    symbol=data["yahoo_symbol"],
                    isin=data["isin"],
                    name=data["name"],
                    sector=stock_config["sector"] if stock_config else None,
                    max_price=stock_config["max"],
                    min_price=stock_config["min"],
                    target_price=stock_config["target"]
                )
                db.session.add(stock)
                db.session.commit()

            # Vérifier si la position existe déjà
            position = Position.query.filter_by(
                portfolio_id=portfolio.id,
                stock_id=stock.id
            ).first()

            if not position:
                position = Position(
                    portfolio_id=portfolio.id,
                    stock_id=stock.id,
                    quantity=data["quantity"],
                    purchase_price=data["buying_price"],
                    purchase_date=datetime.now()
                )
                db.session.add(position)
            else:
                # Mettre à jour les données existantes
                position.quantity = data["quantity"]
                position.purchase_price = data["buying_price"]

        db.session.commit()
        return True, "Portefeuille chargé avec succès"

    except Exception as e:
        db.session.rollback()
        return False, f"Erreur lors du chargement du portefeuille: {str(e)}"
    
def restore_portfolio_from_csv(filepath, portfolio):
    """
    Remplace complètement les positions d'un portefeuille par celles d'un fichier CSV.
    """
    import csv
    from datetime import datetime
    from pea_trading import db
    from pea_trading.portfolios.stock import Stock, Position
    from pea_trading.portfolios.portfolio import Transaction

    try:
        # 🔥 Supprimer les positions existantes et leurs transactions associées
        Position.query.filter_by(portfolio_id=portfolio.id).delete()
        Transaction.query.filter_by(portfolio_id=portfolio.id).delete()
        db.session.commit()

        count = 0
        try:
            csvfile = open(filepath, newline='', encoding='utf-8')
            reader = csv.DictReader(csvfile)
        except UnicodeDecodeError:
            csvfile = open(filepath, newline='', encoding='ISO-8859-1')
            reader = csv.DictReader(csvfile)

        for row in reader:
            symbol = row["Symbole"].strip()
            isin = row["isin"].strip()
            name = row["Nom"].strip()
            quantity = float(row["Quantité"])
            price = float(row["Prix Achat"])
            sector = row.get("Secteur", "Inconnu")

            # Vérifier si l'action existe déjà
            stock = Stock.query.filter_by(symbol=symbol).first()
            if not stock:
                stock = Stock(
                    symbol=symbol,
                    isin=isin,
                    name=name,
                    sector=sector,
                    current_price=price,
                    last_updated=datetime.now()
                )
                db.session.add(stock)
                db.session.flush()

            # Créer la position
            position = Position(
                portfolio_id=portfolio.id,
                stock_id=stock.id,
                quantity=quantity,
                purchase_price=price,
                purchase_date=datetime.now()
            )
            db.session.add(position)

            # Créer la transaction liée
            transaction = Transaction(
                portfolio_id=portfolio.id,
                stock_id=stock.id,
                quantity=quantity,
                price=price,
                type="achat",
                date=datetime.now()
            )
            db.session.add(transaction)

            count += 1

        csvfile.close()
        db.session.commit()
        return count
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Erreur lors de la restauration : {str(e)}")
