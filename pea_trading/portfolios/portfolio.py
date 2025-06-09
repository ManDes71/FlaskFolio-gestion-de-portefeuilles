# pea_trading\portfolios\portfolio.py
from datetime import datetime
from pea_trading import db
from datetime import datetime, timedelta
import math


class Portfolio(db.Model):
    __tablename__ = 'portfolios'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, nullable=False)
    
    # Relations
    positions = db.relationship('Position', backref='portfolio', lazy=True)
    transactions = db.relationship('Transaction', backref='portfolio', lazy=True)
    cash_movements = db.relationship('CashMovement', back_populates='parent_portfolio', lazy=True)


    
    def calculate_total_value(self):
        """Calcule la valeur totale actuelle du portefeuille"""
        return sum(
            position.quantity * position.stock.current_price
            for position in self.positions
            if position.stock.current_price is not None
        )
    
    def calculate_total_cost(self):
        """Calcule le coût total d'acquisition du portefeuille"""
        return sum(
            position.quantity * position.purchase_price
            for position in self.positions
        )
    
    def calculate_portfolio_performance(self):
        """Calcule la performance globale du portefeuille"""
        total_cost = self.calculate_total_cost()
        if total_cost == 0:
            return None
            
        current_value = self.calculate_total_value()
        absolute_gain = current_value - total_cost
        percent_gain = (absolute_gain / total_cost) * 100
        
        return {
            'total_cost': total_cost,
            'current_value': current_value,
            'absolute_gain': absolute_gain,
            'percent_gain': percent_gain
        }
    
    def get_position_weights(self):
        """Calcule la pondération de chaque position dans le portefeuille"""
        total_value = self.calculate_total_value()
        if total_value == 0:
            return {}
            
        return {
            position.stock.symbol: (position.quantity * position.stock.current_price / total_value) * 100
            for position in self.positions
            if position.stock.current_price is not None
        }
    
    def get_sector_allocation(self):
        """Calcule l'allocation par secteur du portefeuille"""
        total_value = self.calculate_total_value()
        if total_value == 0:
            return {}
            
        sector_values = {}
        for position in self.positions:
            if position.stock.current_price is not None:
                sector = position.stock.sector  # Nécessite d'ajouter un champ 'sector' à la classe Stock
                position_value = position.quantity * position.stock.current_price
                sector_values[sector] = sector_values.get(sector, 0) + position_value
        
        return {
            sector: (value / total_value) * 100
            for sector, value in sector_values.items()
        }
    
    def get_portfolio_stats(self, days=30):
        """Calcule les statistiques complètes du portefeuille"""
        performance = self.calculate_portfolio_performance()
        if not performance:
            return None
            
        # Calcul de la volatilité du portefeuille
        weights = self.get_position_weights()
        weighted_volatility = sum(
            (weights.get(position.stock.symbol, 0) / 100) * 
            (position.stock.get_performance_stats(days)['volatility'] or 0)
            for position in self.positions
            if position.stock.current_price is not None
        )
        
        best_position = max(
            self.positions,
            key=lambda p: p.calculate_position_performance()['percent_gain']
            if p.calculate_position_performance() else float('-inf')
        )
        
        worst_position = min(
            self.positions,
            key=lambda p: p.calculate_position_performance()['percent_gain']
            if p.calculate_position_performance() else float('inf')
        )
        
        return {
            **performance,
            'volatility': weighted_volatility,
            'position_weights': self.get_position_weights(),
            'sector_allocation': self.get_sector_allocation(),
            'best_performing_position': {
                'symbol': best_position.stock.symbol,
                'performance': best_position.calculate_position_performance()
            },
            'worst_performing_position': {
                'symbol': worst_position.stock.symbol,
                'performance': worst_position.calculate_position_performance()
            }
        }
    def get_historical_values(self, start_date, end_date):
        """
        Calcule la valeur totale du portefeuille pour chaque jour entre start_date et end_date.
        Pour chaque date, la valeur est obtenue en sommant pour chaque position (quantité * prix de l'action à la date donnée).
        Retourne une liste de dictionnaires sous la forme : [{'date': date, 'value': valeur_totale}, ...]
        """
        historical_values = []
        current_date = start_date
        while current_date <= end_date:
            total_value = 0
            for position in self.positions:
                price = position.stock.get_price_at_date(current_date)
                if price is not None:
                    total_value += position.quantity * price
            historical_values.append({'date': current_date, 'value': total_value})
            current_date += timedelta(days=1)
        return historical_values
    
    def calculate_volatility(self, historical_values):

        """
        Calcule la volatilité du portefeuille à partir de l'historique des valeurs.
        historical_values est une liste de dictionnaires sous la forme [{'date': date, 'value': valeur_totale}, ...].
        La volatilité est calculée comme l'écart-type des rendements journaliers.
        """
        if len(historical_values) < 2:
            return None

        # Tri des valeurs par date (au cas où)
        historical_values = sorted(historical_values, key=lambda x: x['date'])
        values = [entry['value'] for entry in historical_values]
        returns = []

        # Calcul des rendements journaliers
        for i in range(1, len(values)):
            if values[i-1] == 0:
                continue
            returns.append((values[i] - values[i-1]) / values[i-1])

        if len(returns) < 2:
            return None

        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        return math.sqrt(variance)
    
    def calculate_ytd_performance(self):
        """
        Calcule la performance YTD du portefeuille sous forme d'une moyenne pondérée des performances des actions.
        La pondération est basée sur la valeur initiale de chaque position (quantité * prix au début de l'année).
        """
        start_of_year = datetime(datetime.now().year, 1, 1)
        end_date = datetime.utcnow()
        total_weighted_performance = 0.0
        total_initial_value = 0.0
        
        for position in self.positions:
            # Récupérer le prix de l'action au début de l'année
            start_price = position.stock.get_price_at_date(start_of_year)
            if start_price is None:
                continue  # On ignore la position si le prix de départ n'est pas disponible
            
            initial_value = position.quantity * start_price
            
            # Calculer la performance de l'action entre le début de l'année et aujourd'hui
            perf = position.stock.calculate_performance(start_of_year, end_date)
            if perf is None:
                continue  # On ignore si la performance ne peut être calculée
            
            total_weighted_performance += perf * initial_value
            total_initial_value += initial_value
        
        if total_initial_value == 0:
            return None
        
        return total_weighted_performance / total_initial_value
    
    def __repr__(self):
        return f'<Portfolio {self.name}>'
    
class CashMovement(db.Model):
    __tablename__ = 'cash_movements'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # "versement", "retrait", "achat", "vente", "dividende", "frais", etc.
    description = db.Column(db.String(255))

    # ✅ Relation vers le portefeuille
    parent_portfolio = db.relationship('Portfolio', back_populates='cash_movements')

    
class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # "achat" ou "vente"

    # ✅ Ajoute cette relation pour corriger l'erreur
    stock = db.relationship('Stock', backref='transactions')
