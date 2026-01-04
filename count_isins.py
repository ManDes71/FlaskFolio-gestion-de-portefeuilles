#!/usr/bin/env python3
"""Script pour compter les ISINs dans la base de données"""
import sys
sys.path.insert(0, '/app')

from pea_trading.portfolios.stock import Stock
from pea_trading import db, app

with app.app_context():
    # Compter les ISINs uniques
    unique_isins = db.session.query(Stock.isin).distinct().count()
    
    # Compter le total d'actions (avec doublons si même action dans plusieurs portefeuilles)
    total_stocks = Stock.query.count()
    
    # Lister quelques ISINs
    sample_isins = db.session.query(Stock.isin).distinct().limit(10).all()
    
    print(f"📊 Nombre d'ISINs uniques dans votre BDD: {unique_isins}")
    print(f"📊 Nombre total d'entrées Stock: {total_stocks}")
    print(f"\n🔍 Exemple d'ISINs dans votre BDD:")
    for isin in sample_isins:
        stock = Stock.query.filter_by(isin=isin[0]).first()
        print(f"  - {isin[0]} : {stock.name if stock else 'N/A'}")
