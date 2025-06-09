# pea_trading/services/alertes.py

def detecter_alertes(portfolio):
    alertes_vente = []
    alertes_achat = []

    for position in portfolio.positions:
        stock = position.stock

        if stock.current_price is None:
            continue  # ⚠️ Ne pas traiter des données incomplètes

        # ✅ Vente : si current >= max (et max défini)
        if stock.max_price is not None and stock.current_price >= stock.max_price:
            stock.limite = stock.max_price
            stock.ecart_pct = (stock.current_price - stock.max_price) / stock.max_price * 100
            stock.type_alerte = "vente"
            #alertes_vente.append(stock)
            alertes_achat.append(stock)

        # ✅ Achat : si current <= min (et min défini)
        elif stock.min_price is not None and stock.current_price <= stock.min_price:
            stock.limite = stock.min_price
            stock.ecart_pct = (stock.current_price - stock.min_price) / stock.min_price * 100
            stock.type_alerte = "achat"
            #alertes_achat.append(stock)
            alertes_vente.append(stock)

    return {
        "alertes_vente": alertes_vente,
        "alertes_achat": alertes_achat
    }
