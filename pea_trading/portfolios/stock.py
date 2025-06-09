# pea_trading\portfolios\stock.py
from datetime import datetime, timedelta
from pea_trading import db
from sqlalchemy import func
from typing import Dict,  List


class Stock(db.Model):
    __tablename__ = 'stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), unique=True, nullable=False)
    isin = db.Column(db.String(12), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    sector = db.Column(db.String(50))  # Nouveau champ pour le secteur
    current_price = db.Column(db.Float)
    max_price = db.Column(db.Float)
    min_price = db.Column(db.Float)
    target_price = db.Column(db.Float)

    last_updated = db.Column(db.DateTime, default=datetime.now)
    
    # Relations
    positions = db.relationship('Position', backref='stock', lazy=True)
    price_history = db.relationship('StockPriceHistory', backref='stock', lazy=True)
    
    def get_price_at_date(self, date):
        """Récupère le prix de clôture à une date donnée"""
        history = StockPriceHistory.query.filter_by(
            stock_id=self.id
        ).filter(
            StockPriceHistory.date <= date
        ).order_by(
            StockPriceHistory.date.desc()
        ).first()
        
        return history.close_price if history else None

    def calculate_performance(self, start_date, end_date=None):
        """Calcule la performance entre deux dates"""
        if end_date is None:
            end_date = datetime.utcnow()
            
        start_price = self.get_price_at_date(start_date)
        end_price = self.get_price_at_date(end_date)
        
        if not start_price or not end_price:
            return None
            
        return ((end_price - start_price) / start_price) * 100
    
    def get_performance_stats(self, days=30):
        """Calcule les statistiques de performance sur une période"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        history = StockPriceHistory.query.filter_by(
            stock_id=self.id
        ).filter(
            StockPriceHistory.date.between(start_date, end_date)
        ).order_by(
            StockPriceHistory.date.asc()
        ).all()
        
        if not history:
            return None
            
        return {
            'performance': self.calculate_performance(start_date, end_date),
            'highest_price': max(h.high_price for h in history),
            'lowest_price': min(h.low_price for h in history),
            'avg_volume': sum(h.volume for h in history) / len(history),
            'volatility': self._calculate_volatility(history)
        }
    
    def _calculate_volatility(self, history):
        """Calcule la volatilité basée sur les prix de clôture"""
        if len(history) < 2:
            return None
            
        prices = [h.close_price for h in history]
        returns = [(prices[i] - prices[i-1])/prices[i-1] for i in range(1, len(prices))]
        avg_return = sum(returns) / len(returns)
        squared_diff = sum((r - avg_return) ** 2 for r in returns)
        return (squared_diff / (len(returns) - 1)) ** 0.5
    
    def get_stock_history_table(self, period: str = '1M') -> List[Dict]:
        """
        Prépare l'historique des prix pour l'affichage en tableau
        """
        # Définir la période
        end_date = datetime.utcnow()
        if period == '1M':
            start_date = end_date - timedelta(days=30)
        elif period == '3M':
            start_date = end_date - timedelta(days=90)
        elif period == '6M':
            start_date = end_date - timedelta(days=180)
        elif period == '1Y':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime(end_date.year, 1, 1)  # YTD

        # Récupérer l'historique
        history = StockPriceHistory.query.filter(
            StockPriceHistory.stock_id == self.id,
            StockPriceHistory.date.between(start_date, end_date)
        ).order_by(StockPriceHistory.date.desc()).all()

        # Formater les données pour le tableau
        return [{
            'date': h.date.isoformat(),
            'open_price': h.open_price,
            'high_price': h.high_price,
            'low_price': h.low_price,
            'close_price': h.close_price,
            'volume': h.volume,
            'daily_change': ((h.close_price - h.open_price) / h.open_price * 100)
        } for h in history]
    
    def __repr__(self):
        return f'<Stock {self.symbol}>'

class Position(db.Model):
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.now)
    
    def calculate_position_performance(self):
        """Calcule la performance de la position"""
        current_price = self.stock.current_price
        if not current_price:
            print('not current_price !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            return None
            
        total_cost = self.quantity * self.purchase_price
        current_value = self.quantity * current_price
        absolute_gain = current_value - total_cost
        percent_gain = (absolute_gain / total_cost) * 100
        
        return {
            'cost_basis': total_cost,
            'current_value': current_value,
            'absolute_gain': absolute_gain,
            'percent_gain': percent_gain
        }
    
    def __repr__(self):
        return f'<Position {self.stock_id} in Portfolio {self.portfolio_id}>'

class StockPriceHistory(db.Model):
    __tablename__ = 'stock_price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    open_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger)
    
    __table_args__ = (
        db.Index('idx_stock_date', 'stock_id', 'date'),
    )
    
    def __repr__(self):
        return f'<StockPriceHistory {self.stock_id} on {self.date}>'