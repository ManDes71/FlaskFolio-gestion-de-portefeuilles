from pea_trading import db
from pea_trading.portfolios.portfolio import Transaction, CashMovement
from datetime import datetime

def ajouter_transaction_et_mouvement(portfolio_id, stock_id, quantity, price, type_op, description=None, date=None, auto_commit=True):
    """
    Crée une transaction et un mouvement de cash liés.
    
    - type_op: 'achat' ou 'vente'
    """
    if date is None:
        date = datetime.now()

    transaction = Transaction(
        portfolio_id=portfolio_id,
        stock_id=stock_id,
        quantity=quantity,
        price=price,
        date=date,
        type=type_op
    )
    db.session.add(transaction)

    montant = price * quantity
    if type_op == 'achat':
        montant = -montant  # Sortie d'argent

    mouvement = CashMovement(
        portfolio_id=portfolio_id,
        amount=montant,
        type=type_op,
        date=date,
        description=description or f"{type_op.title()} de {quantity}x à {price:.2f}€"
    )
    db.session.add(mouvement)

    if auto_commit:
        db.session.commit()
        
    return transaction, mouvement

def update_transaction_et_cash(transaction_id, new_quantity=None, new_price=None, new_description=None,new_date=None):
    from pea_trading import db
    from pea_trading.portfolios.portfolio import Transaction, CashMovement

    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        raise ValueError("Transaction non trouvée")

    # Trouver le mouvement de cash correspondant
    mouvement = CashMovement.query.filter_by(
        portfolio_id=transaction.portfolio_id,
        date=transaction.date,
        amount=(transaction.price * transaction.quantity) * (-1 if transaction.type == 'achat' else 1)
    ).first()

    # Mise à jour
    if new_quantity:
        transaction.quantity = new_quantity
    if new_price:
        transaction.price = new_price
    if new_description:
        if mouvement:
            mouvement.description = new_description
    if new_date:
        transaction.date = new_date
        if mouvement:
            mouvement.date = new_date        

    # Mettre à jour le montant du cash movement
    if mouvement:
        new_amount = transaction.price * transaction.quantity
        mouvement.amount = -new_amount if transaction.type == 'achat' else new_amount

    db.session.commit()

