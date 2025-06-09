import csv
import os
from datetime import datetime
from flask import current_app
from pea_trading import db
from pea_trading.portfolios.portfolio import Portfolio, Transaction, CashMovement
from pea_trading.portfolios.stock import Stock, Position, StockPriceHistory


def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def process_stocks_csv_file(filename="stocks_export.csv"):
    filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    print(f"Import en cours de : {filepath}")
    imported_symbols = set()
    try:
        try:
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader)
                for row in reader:
                    symbol, isin, name, sector, current_price, max_price, min_price, target_price = row
                    imported_symbols.add(symbol)
                    stock = Stock.query.filter_by(symbol=symbol).first()
                    if stock:
                        stock.isin = isin
                        stock.name = name
                        stock.sector = sector
                        stock.current_price = safe_float(current_price)
                        stock.max_price = safe_float(max_price)
                        stock.min_price = safe_float(min_price)
                        stock.target_price = safe_float(target_price)
                    else:
                        stock = Stock(
                            symbol=symbol,
                            isin=isin,
                            name=name,
                            sector=sector,
                            current_price=safe_float(current_price),
                            max_price=safe_float(max_price),
                            min_price=safe_float(min_price),
                            target_price=safe_float(target_price)
                        )
                        db.session.add(stock)
        except UnicodeDecodeError:
            with open(filepath, newline='', encoding='ISO-8859-1') as csvfile:
                reader = csv.reader(csvfile)
                next(reader)
                for row in reader:
                    symbol, isin, name, sector, current_price, max_price, min_price, target_price = row
                    imported_symbols.add(symbol)
                    stock = Stock.query.filter_by(symbol=symbol).first()
                    if stock:
                        stock.isin = isin
                        stock.name = name
                        stock.sector = sector
                        stock.current_price = safe_float(current_price)
                        stock.max_price = safe_float(max_price)
                        stock.min_price = safe_float(min_price)
                        stock.target_price = safe_float(target_price)
                    else:
                        stock = Stock(
                            symbol=symbol,
                            isin=isin,
                            name=name,
                            sector=sector,
                            current_price=safe_float(current_price),
                            max_price=safe_float(max_price),
                            min_price=safe_float(min_price),
                            target_price=safe_float(target_price)
                        )
                        db.session.add(stock)

        # Supprimer les actions absentes du CSV
        existing_symbols = {s.symbol for s in Stock.query.all()}
        for sym in existing_symbols - imported_symbols:
            to_delete = Stock.query.filter_by(symbol=sym).first()
            if to_delete:
                StockPriceHistory.query.filter_by(stock_id=to_delete.id).delete()
                db.session.delete(to_delete)

        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        return False, str(e)

def process_stock_history_csv_file(filename="historique_stocks.csv"):
    filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    print(f"Import en cours de : {filepath}")
    try:
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            historique_par_stock = {}

            for row in reader:
                stock_symbol, date_str, stock_name, open_price, close_price, high_price, low_price, volume = row
                stock = Stock.query.filter_by(symbol=stock_symbol).first()
                if not stock:
                    continue

                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                if stock.id not in historique_par_stock:
                    historique_par_stock[stock.id] = []

                historique_par_stock[stock.id].append(
                    StockPriceHistory(
                        stock_id=stock.id,
                        date=date_obj,
                         open_price=safe_float(open_price),
                        close_price=safe_float(close_price),
                        high_price=safe_float(high_price),
                        low_price=safe_float(low_price),
                        volume=int(volume) if volume.isdigit() else 0
                    )
                )

            for stock_id, entries in historique_par_stock.items():
                StockPriceHistory.query.filter_by(stock_id=stock_id).delete()
                db.session.add_all(entries)

        db.session.commit()
        total_lignes = sum(len(v) for v in historique_par_stock.values())
        return True, total_lignes
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def process_portfolio_positions_csv(portfolio_name, filename):
    filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    imported = 0

    try:
        portfolio = Portfolio.query.filter_by(name=portfolio_name).first()
        if not portfolio:
            return False, f"Portefeuille '{portfolio_name}' non trouvé."

        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                symbol, isin, name, quantity, purchase_price, sector = row
                stock = Stock.query.filter_by(symbol=symbol).first()
                if not stock:
                    stock = Stock(symbol=symbol, isin=isin, name=name, sector=sector)
                    db.session.add(stock)
                    db.session.flush()  # get id without commit

                position = next((p for p in portfolio.positions if p.stock_id == stock.id), None)
                if position:
                    position.quantity = float(quantity)
                    position.purchase_price = float(purchase_price)
                else:
                    position = Position(
                        portfolio_id=portfolio.id,
                        stock_id=stock.id,
                        quantity=float(quantity),
                        purchase_price=float(purchase_price)
                    )
                    db.session.add(position)
                imported += 1

        db.session.commit()
        return True, f"{imported} positions importées"
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def process_portfolio_transactions_csv(portfolio_name, filename):
    filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    imported = 0

    try:
        portfolio = Portfolio.query.filter_by(name=portfolio_name).first()
        if not portfolio:
            return False, f"Portefeuille '{portfolio_name}' non trouvé."
        
        # 🧹 Supprimer les transactions existantes
        Transaction.query.filter_by(portfolio_id=portfolio.id).delete()
        
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                date_str, type_, symbol, quantity, price = row
                stock = Stock.query.filter_by(symbol=symbol).first()
                if not stock:
                    continue  # ou créer le stock ici si nécessaire
                tx = Transaction(
                    portfolio_id=portfolio.id,
                    stock_id=stock.id,
                    date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                    type=type_,
                    quantity=float(quantity),
                    price=float(price)
                )
                db.session.add(tx)
                imported += 1

        db.session.commit()
        return True, f"{imported} Transactions importées avec succès"
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def process_portfolio_cash_movements_csv(portfolio_name, filename):
    filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    imported = 0

    try:
        portfolio = Portfolio.query.filter_by(name=portfolio_name).first()
        if not portfolio:
            return False, f"Portefeuille '{portfolio_name}' non trouvé."
        
        # 🧹 Supprimer les mouvements existants
        CashMovement.query.filter_by(portfolio_id=portfolio.id).delete()

        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                date_str, type_, amount, description = row
                mv = CashMovement(
                    portfolio_id=portfolio.id,
                    date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                    type=type_,
                    amount=float(amount),
                    description=description
                )
                db.session.add(mv)
                imported += 1

        db.session.commit()
        return True, f"{imported} Mouvements de trésorerie importés avec succès"
    except Exception as e:
        db.session.rollback()
        return False, str(e)
