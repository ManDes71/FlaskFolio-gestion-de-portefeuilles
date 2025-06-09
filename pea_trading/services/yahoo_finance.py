# pea_trading\services\yahoo_finance.py
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from pea_trading import db
from pea_trading.portfolios.stock import Stock, StockPriceHistory
from config.stocks import get_all_yahoo_symbols, STOCKS_CONFIG
import time

# Paramètres de cache
CACHE_TIMEOUT = timedelta(minutes=30)
ticker_cache = {}

def get_yf_ticker(symbol):
    now = datetime.now()
    if symbol in ticker_cache:
        ticker_obj, timestamp = ticker_cache[symbol]
        if now - timestamp < CACHE_TIMEOUT:
            return ticker_obj
    ticker = yf.Ticker(symbol)
    ticker_cache[symbol] = (ticker, now)
    return ticker

# Cache des données individuelles de stock
stock_data_cache = {}

def get_stock_data_cached(symbol: str, ttl: timedelta = CACHE_TIMEOUT) -> Optional[Dict]:
    """
    Récupère les données d'une action depuis Yahoo Finance avec mise en cache
    
    Args:
        symbol: Symbole Yahoo Finance
        ttl: Durée de vie du cache
    
    Returns:
        Dict contenant les informations de l'action ou None si erreur
    """
    now = datetime.now()
    if symbol in stock_data_cache:
        data, timestamp = stock_data_cache[symbol]
        if now - timestamp < ttl:
            return data

    data = get_stock_data(symbol)
    if data:
        stock_data_cache[symbol] = (data, now)
    return data


def get_stock_data(symbol: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Optional[Dict]:
    """
    Récupère les données d'une action depuis Yahoo Finance
    
    Args:
        symbol: Symbole Yahoo Finance de l'action
        start_date: Date de début (par défaut: 1 an en arrière)
        end_date: Date de fin (par défaut: aujourd'hui)
    
    Returns:
        Dict contenant les informations de l'action ou None si erreur
    """
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()

        ticker = get_yf_ticker(symbol)
        info = ticker.info
        
        return {
            'current_price': info.get('currentPrice'),
            'previous_close': info.get('previousClose'),
            'open': info.get('open'),
            'day_high': info.get('dayHigh'),
            'day_low': info.get('dayLow'),
            'volume': info.get('volume'),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('forwardPE'),
            'dividend_yield': info.get('dividendYield'),
            'fifty_day_average': info.get('fiftyDayAverage'),
            'two_hundred_day_average': info.get('twoHundredDayAverage')
        }
    except Exception as e:
        print(f"Erreur lors de la récupération des données (yahoo - get_stock_data) pour {symbol}: {str(e)}")
        return None



def get_historical_data(symbol: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
    """
    Récupère l'historique des cours d'une action
    
    Args:
        symbol: Symbole Yahoo Finance de l'action
        start_date: Date de début (par défaut: 1 an en arrière)
        end_date: Date de fin (par défaut: aujourd'hui)
    
    Returns:
        DataFrame pandas contenant l'historique ou None si erreur
    """
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()

        ticker = get_yf_ticker(symbol)
        history = ticker.history(start=start_date, end=end_date)
        return history
    except Exception as e:
        print(f"Erreur lors de la récupération de l'historique pour {symbol}: {str(e)}")
        return None

def update_stock_prices() -> Dict[str, bool]:
    """
    Met à jour les prix de toutes les actions dans la base de données
    
    Returns:
        Dict indiquant le succès de la mise à jour pour chaque symbole
    """
    print("coucou")
    results = {}
    symbols = get_all_yahoo_symbols()
    
    for symbol in symbols:
        try:
            #time.sleep(1)
            #data = get_stock_data(symbol)
            data = get_stock_data_cached(symbol)
            if not data:
                results[symbol] = False
                continue
                
            stock = Stock.query.filter_by(symbol=symbol).first()
            print(f"Vérification : {symbol} -> {stock}")
            if  stock is None:
                print(f"⚠️ Données incomplètes pour {symbol}, skipping.")
                continue

            price = data.get("current_price")
            if price is None:
                print(f"⚠️ Pas de `current_price` pour {symbol}, utilisation de `previous_close`.")
                price = data.get("previous_close")
            if stock:
                stock.current_price = price
                stock.last_updated = datetime.now()
                db.session.commit()
                print(f"✅ Mise à jour (yahoo - update_stock_prices): {symbol} -> {data['current_price']}")
                results[symbol] = True
            else:
                # Trouver la configuration correspondante
                print(f"⚠️ Stock {symbol} introuvable en base.")
                stock_config = next(
                    (conf for conf in STOCKS_CONFIG.values() if conf['yahoo_symbol'] == symbol),
                    None
                )
                if stock_config:
                    new_stock = Stock(
                        symbol=symbol,
                        name=stock_config['name'],
                        sector=stock_config['sector'],  # À remplir manuellement ou via une autre source
                        current_price=price
                    )
                    db.session.add(new_stock)
                    db.session.commit()
                    results[symbol] = True
                else:
                    results[symbol] = False
        except Exception as e:
            print(f"Erreur lors de la mise à jour de {symbol}: {str(e)}")
            results[symbol] = False
            
    return results

def update_historical_prices(days: int = 365) -> Dict[str, bool]:
    """
    Met à jour l'historique des prix pour toutes les actions
    
    Args:
        days: Nombre de jours d'historique à récupérer
        
    Returns:
        Dict indiquant le succès de la mise à jour pour chaque symbole
    """
    results = {}
    symbols = get_all_yahoo_symbols()
    start_date = datetime.now() - timedelta(days=days) +  timedelta(days=1)
    print(start_date)
    
    for symbol in symbols:
        try:
            history = get_historical_data(symbol, start_date)
            if history is None:
                results[symbol] = False
                continue
                
            stock = Stock.query.filter_by(symbol=symbol).first()
            if not stock:
                results[symbol] = False
                continue
                
            # Supprimer l'ancien historique pour cette période
            StockPriceHistory.query.filter(
                StockPriceHistory.stock_id == stock.id,
                StockPriceHistory.date >= start_date
            ).delete()
            
            # Ajouter les nouvelles données historiques
            for index, row in history.iterrows():
                price_history = StockPriceHistory(
                    stock_id=stock.id,
                    date=index,
                    open_price=row['Open'],
                    high_price=row['High'],
                    low_price=row['Low'],
                    close_price=row['Close'],
                    volume=row['Volume']
                )
                db.session.add(price_history)
                last_row = (index, row)  # Mémoriser la dernière ligne

            # Afficher la dernière valeur après la boucle
            if last_row:
                index, row = last_row
                print(f"Dernière valeur insérée pour {stock.symbol} :")
                print(f"Date: {index.strftime('%Y-%m-%d')}, Close: {row['Close']}, Volume: {row['Volume']}")
            
            db.session.commit()
            results[symbol] = True
            
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'historique (yahoo - )de {symbol}: {str(e)}")
            results[symbol] = False
            db.session.rollback()
            
    return results

def get_stock_alerts() -> List[Dict]:
    """
    Vérifie les alertes pour toutes les actions (dépassement des seuils min/max)
    
    Returns:
        Liste des alertes générées
    """
    alerts = []
    for stock_code, config in STOCKS_CONFIG.items():
        stock = Stock.query.filter_by(symbol=config['yahoo_symbol']).first()
        if not stock or not stock.current_price:
            continue
            
        current_price = stock.current_price
        
        if current_price > config['max']:
            alerts.append({
                'stock': config['name'],
                'type': 'above_max',
                'threshold': config['max'],
                'current_price': current_price
            })
            
        if current_price < config['min']:
            alerts.append({
                'stock': config['name'],
                'type': 'below_min',
                'threshold': config['min'],
                'current_price': current_price
            })
            
    return alerts