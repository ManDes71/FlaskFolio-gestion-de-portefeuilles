import os
import csv
from pea_trading.portfolios.stock import Stock, StockPriceHistory
from flask import  current_app
#from datetime import datetime


def export_stocks_to_csv(filename="stocks_export.csv"):
    filepath = os.path.join(current_app.root_path, 'static', 'exports', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    print(f"Export en cours vers : {filepath}")

    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Symbole', 'ISIN', 'Nom', 'Secteur', 'Dernier Prix', 'Val max', 'Val min', 'Target'])
        for stock in Stock.query.all():
            print("ok")
            writer.writerow([
                stock.symbol, stock.isin, stock.name, stock.sector,
                stock.current_price, stock.max_price, stock.min_price, stock.target_price
            ])
    return filepath

def export_stock_history_to_csv(filename="historique_stocks.csv"):
    filepath = os.path.join(current_app.root_path, 'static', 'exports', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    print(f"Export en cours vers : {filepath}")

    histories = StockPriceHistory.query.join(Stock).order_by(Stock.symbol, StockPriceHistory.date).all()
    seen = set()
    unique_histories = []

    for h in histories:
        key = (h.stock.symbol, h.date.date())
        if key not in seen:
            seen.add(key)
            unique_histories.append(h)

    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['yahoo_symbol', 'date', 'nom', 'ouverture', 'cloture', 'haut', 'bas', 'volume'])
        for h in unique_histories:
            writer.writerow([
                h.stock.symbol,
                h.date.strftime('%Y-%m-%d'),
                h.stock.name,
                h.open_price,
                h.close_price,
                h.high_price,
                h.low_price,
                h.volume
            ])
    return filepath

def export_portfolio_positions_to_csv(portfolio, filename):
    filepath = os.path.join(current_app.root_path, "static", "exports", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Symbole", "ISIN", "Nom", "Quantité", "Prix d'achat", "Secteur"])
        for position in portfolio.positions:
            writer.writerow([
                position.stock.symbol,
                position.stock.isin,
                position.stock.name,
                position.quantity,
                position.purchase_price,
                position.stock.sector or ""
            ])
    return filepath


def export_portfolio_transactions_to_csv(portfolio, filename):
    filepath = os.path.join(current_app.root_path, "static", "exports", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Type", "Symbole", "Quantité", "Prix"])
        for tx in sorted(portfolio.transactions, key=lambda t: t.date):
            writer.writerow([
                tx.date.strftime('%Y-%m-%d'),
                tx.type,
                tx.stock.symbol if tx.stock else "",
                tx.quantity,
                tx.price
            ])
    return filepath


def export_portfolio_cash_movements_to_csv(portfolio, filename):
    filepath = os.path.join(current_app.root_path, "static", "exports", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Type", "Montant", "Description"])
        for m in sorted(portfolio.cash_movements, key=lambda x: x.date):
            writer.writerow([
                m.date.strftime('%Y-%m-%d'),
                m.type,
                m.amount,
                m.description or ""
            ])
    return filepath
