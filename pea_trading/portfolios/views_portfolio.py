# pea_trading\portfolios\views_portfolio.py
from flask import render_template,request,Blueprint,jsonify, session, redirect, url_for, flash
from flask_mail import Message
#from pea_trading import mail
from datetime import datetime, timedelta
from pea_trading.portfolios.portfolio import Portfolio
from pea_trading.portfolios.stock import Stock, StockPriceHistory
from pea_trading.portfolios.stock import StockPriceHistory
from pea_trading.portfolios.portfolio import Transaction, CashMovement
from pea_trading.services.portfolio_loader import load_portfolio_data
from pea_trading.services.technical_indicators import compute_ichimoku
from datetime import datetime

import pandas as pd
import os

portfolios = Blueprint('portfolios',__name__)

#http://127.0.0.1:5000/test-alertes-mail


#from app.models.portfolio import Portfolio
#from app.models.stock import Stock, StockPriceHistory
#from sqlalchemy import func

def get_alertes_et_bornes(portfolio: Portfolio):
    alertes_vente = []
    alertes_achat = []
    bornes_min_a_remonter = []
    bornes_min_a_abaisser = []

    portefeuille_symbols = {position.stock.symbol for position in portfolio.positions}
    all_stocks = Stock.query.all()

    for stock in all_stocks:
        if stock.current_price is None:
            continue

        in_portfolio = stock.symbol in portefeuille_symbols

        if in_portfolio:
            # Signal de vente
            if (stock.target_price and stock.current_price >= stock.target_price) or \
               (stock.min_price and stock.current_price <= stock.min_price):
                alertes_vente.append(stock)

            # Borne max atteinte = min à remonter
            if stock.max_price and stock.current_price >= stock.max_price:
                bornes_min_a_remonter.append(stock)

        else:
            # Signal d'achat
            if stock.max_price and stock.current_price >= stock.max_price:
                alertes_achat.append(stock)

            # Borne min atteinte = min à ajuster
            if stock.min_price and stock.current_price <= stock.min_price:
                bornes_min_a_abaisser.append(stock)

    return {
        "alertes_vente": alertes_vente,
        "alertes_achat": alertes_achat,
        "bornes_min_a_remonter": bornes_min_a_remonter,
        "bornes_min_a_abaisser": bornes_min_a_abaisser
    }

def envoyer_email_alertes(email, portfolio, alertes, app, mail):
    if not alertes["alertes_vente"] and not alertes["alertes_achat"]:
        print("✅ Aucune alerte, email non envoyé.")
        return

    msg = Message(
        subject=f"🚨 {len(alertes['alertes_vente']) + len(alertes['alertes_achat'])} alerte(s) détectée(s) - {portfolio.name}",
        recipients=[email]
    )
    msg.body = render_template("emails/alertes.txt", portfolio=portfolio, **alertes)
    msg.html = render_template("emails/alertes.html", portfolio=portfolio, **alertes)
    
    with app.app_context():
        mail.send(msg)
    print("📤 Email envoyé à", email)

@portfolios.route('/')
def index():
    """ Vérifie si un portefeuille est sélectionné, sinon redirige vers la sélection """
    portfolio_id = session.get('selected_portfolio_id')

    if not portfolio_id:  # Si aucun portefeuille n'est sélectionné, aller à la liste des portefeuilles
        return redirect(url_for('portfolios.list_portfolios'))

    portfolio = Portfolio.query.get(portfolio_id)
    positions_tries = sorted(portfolio.positions, key=lambda p: p.stock.name.lower())
    if not portfolio:  # Si le portefeuille n'existe plus en base
        session.pop('selected_portfolio_id', None)
        return redirect(url_for('portfolios.list_portfolios'))
    
    #portfolio = Portfolio.query.first()  # Ou utilisez l'ID du portefeuille actif

    print(f"Portfolio chargé : {portfolio}")  # ✅ Vérifie si un portefeuille est trouvé

    if portfolio:
        sector_allocation = portfolio.get_sector_allocation() or {}
        print(f"Allocation sectorielle : {sector_allocation}")  # ✅ Debug pour voir les données reçues
    else:
        print("❌ Aucun portefeuille trouvé !")
        sector_allocation = {}

    sector_labels = list(sector_allocation.keys()) or []
    sector_values = list(sector_allocation.values()) or []

    print(f"Labels: {sector_labels}, Valeurs: {sector_values}")  # ✅ Debug final avant affichage
    
    # Préparer les données pour les graphiques
    #sector_allocation = portfolio.get_sector_allocation()
    #sector_labels = list(sector_allocation.keys())
    #sector_values = list(sector_allocation.values())
    
    # Top 5 positions
    positions = sorted(
        portfolio.positions,
        key=lambda p: p.quantity * p.stock.current_price,
        reverse=True
    )[:5]

    top_positions_labels = [p.stock.symbol for p in positions]
    top_positions_values = [p.quantity * p.stock.current_price for p in positions]
    
    return render_template('index.html',
                         portfolio=portfolio,
                         positions=positions_tries,
                         sector_labels=sector_labels,
                         sector_values=sector_values,
                         top_positions_labels=top_positions_labels,
                         top_positions_values=top_positions_values)

@portfolios.route('/portfolios')
def list_portfolios():
    """ Affiche la liste des portefeuilles disponibles """
    portfolios = Portfolio.query.all()

    # Détection du portefeuille sélectionné via URL ou session
    portfolio_id = request.args.get("portfolio_id", type=int) or session.get('selected_portfolio_id')
    selected_portfolio = Portfolio.query.get(portfolio_id) if portfolio_id else None

    # Stocker le choix dans la session (si trouvé dans URL)
    if portfolio_id:
        session['selected_portfolio_id'] = portfolio_id

    alertes_data = {}
    if selected_portfolio:
        alertes_data = get_alertes_et_bornes(selected_portfolio)

    return render_template(
        'select_portfolio.html',
        portfolios=portfolios,
        selected_portfolio=selected_portfolio,
        **alertes_data)

@portfolios.route('/portfolios/select/<int:portfolio_id>')
def select_portfolio(portfolio_id):
    """ Stocke le portefeuille sélectionné en session et redirige vers l'index """
    session['selected_portfolio_id'] = portfolio_id
    portfolio = Portfolio.query.get(portfolio_id)
    flash(f'✅ Portefeuille « {portfolio.name} » sélectionné', 'success')
    #return redirect(url_for('portfolios.view_portfolio', portfolio_id=portfolio_id))
    return redirect(url_for('portfolios.index'))

@portfolios.route('/portfolios/<int:portfolio_id>')
def view_portfolio(portfolio_id):
    """ Affiche les positions du portefeuille sélectionné """
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    positions_tries = sorted(portfolio.positions, key=lambda p: p.stock.name.lower())
    return render_template('index.html', portfolio=portfolio, positions=positions_tries)

@portfolios.route('/portfolios/<int:portfolio_id>/history')
def view_portfolio_history(portfolio_id):
    """ Affiche l'historique du portefeuille sélectionné """
    portfolio = Portfolio.query.get_or_404(portfolio_id)

    # Calculer la performance du portefeuille
    performance = portfolio.calculate_portfolio_performance() if portfolio else {}

    current_value = performance.get('current_value', 0)  # Évite les valeurs None
    total_gain = performance.get('absolute_gain', 0)
    ytd_performance = portfolio.calculate_ytd_performance() if hasattr(portfolio, 'calculate_ytd_performance') else 0

    # Historique des valeurs du portefeuille
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    history = portfolio.get_historical_values(start_date, end_date) if portfolio else []

    volatility = portfolio.calculate_volatility(history) * 100 if history else 0

    # Préparer les données pour le graphique
    dates = [h['date'].strftime('%Y-%m-%d') for h in history] if history else []
    values = [h['value'] for h in history] if history else []

    return render_template('portfolio_history.html',
                           portfolio=portfolio,
                           current_value=current_value,
                           total_gain=total_gain,
                           ytd_performance=ytd_performance,
                           volatility=volatility,
                           dates=dates,
                           values=values)


@portfolios.route('/stock/<symbol>')
def stock_history(symbol):
    stock = Stock.query.filter_by(symbol=symbol).first_or_404()
    portfolio_id = session.get('selected_portfolio_id')
    
    # Calculer les statistiques
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    history = StockPriceHistory.query.filter(
        StockPriceHistory.stock_id == stock.id,
        StockPriceHistory.date.between(start_date, end_date)
    ).order_by(StockPriceHistory.date.asc()).all()
    
    monthly_change = stock.calculate_performance(start_date)
    avg_volume = int(sum(h.volume for h in history) / len(history)) if history else 0
    volatility = stock._calculate_volatility(history) * 100 if history else 0
    purchase_price = None
    if portfolio_id:
        portfolio = Portfolio.query.get(portfolio_id)
        position = next((p for p in portfolio.positions if p.stock_id == stock.id), None)
        if position:
            purchase_price = position.purchase_price
    #history = stock.get_stock_history()

    historical_data = StockPriceHistory.query.filter(
        StockPriceHistory.stock_id == stock.id,
        StockPriceHistory.date.between(start_date, end_date)
    ).order_by(StockPriceHistory.date.desc()).all()
    
    # Données pour le graphique
    dates = [h.date.strftime('%Y-%m-%d') for h in history]
    prices = [h.close_price for h in history]
    mm20 = []
    if len(prices) >= 20:
        mm20 = [sum(prices[i-19:i+1])/20 for i in range(19, len(prices))]
        # Ajouter des None devant pour aligner avec les dates
        mm20 = [None]*19 + mm20


     # Préparer les données pour Ichimoku
    history_dict = [{
    'date': h.date.strftime('%Y-%m-%d'),
    'high_price': h.high_price,
    'low_price': h.low_price,
    'close_price': h.close_price
    } for h in history]

    ichimoku = compute_ichimoku(history_dict)
    print(ichimoku)
    
    return render_template('stock_history.html',
                         stock=stock,
                         monthly_change=monthly_change,
                         avg_volume=avg_volume,
                         volatility=volatility,
                         dates=dates,
                         prices=prices,
                         mm20=mm20,
                         historical_data=historical_data,
                         history=history,
                         max_price=stock.max_price,
                         min_price=stock.min_price,
                         target_price=stock.target_price,
                         ichimoku=ichimoku,
                         purchase_price=purchase_price)

@portfolios.route('/portfolio/history')
def portfolio_history():
    portfolio = Portfolio.query.first()
    performance = portfolio.calculate_portfolio_performance()
    
    current_value = performance['current_value']
    total_gain = performance['absolute_gain']
    
    # Utilisation de la nouvelle méthode pour obtenir l'historique de valeur
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    history = portfolio.get_historical_values(start_date, end_date)
    volatility = portfolio.calculate_volatility(history) * 100 if history else 0  # à adapter si besoin
    
    # Préparation des données pour le graphique
    dates = [h['date'].strftime('%Y-%m-%d') for h in history]
    values = [h['value'] for h in history]
    
    return render_template('portfolio_history.html',
                           current_value=current_value,
                           ytd_performance=portfolio.calculate_ytd_performance(),
                           total_gain=total_gain,
                           volatility=volatility,
                           dates=dates,
                           values=values)
@portfolios.route('/api/stock/<symbol>/history/<period>')
def api_stock_history(symbol, period):
    stock = Stock.query.filter_by(symbol=symbol).first_or_404()
    
    # Déterminer la période
    end_date =datetime.now()
    if period == '1M':
        start_date = end_date - timedelta(days=30)
    elif period == '3M':
        start_date = end_date - timedelta(days=90)
    elif period == '6M':
        start_date = end_date - timedelta(days=180)
    elif period == '1Y':
        start_date = end_date - timedelta(days=365)
    elif period == '2Y':
        start_date = end_date - timedelta(days=730)    
    else:
        start_date = end_date - timedelta(days=30)
    
# Si format=table est spécifié, renvoyer les données pour le tableau
    if request.args.get('format') == 'table':
        history = Stock.get_stock_history_table(stock, period)
        return jsonify(history)

    history = StockPriceHistory.query.filter(
        StockPriceHistory.stock_id == stock.id,
        StockPriceHistory.date.between(start_date, end_date)
    ).order_by(StockPriceHistory.date.asc()).all()
    
    return jsonify({
        'dates': [h.date.strftime('%Y-%m-%d') for h in history],
        'prices': [h.close_price for h in history]
    })

@portfolios.route('/api/portfolio/history/<period>')
def api_portfolio_history(period):
    portfolio_id = session.get("selected_portfolio_id")
    if not portfolio_id:
        return jsonify({"error": "Aucun portefeuille sélectionné."}), 400

    portfolio = Portfolio.query.get(portfolio_id)
    if not portfolio:
        return jsonify({"error": "Portefeuille introuvable."}), 404
    
    print("/api/portfolio/history/<period> portefeuille selectionné :", portfolio_id)
    
    # Déterminer la période
    end_date = datetime.now()
    if period == '1M':
        start_date = end_date - timedelta(days=30)
    elif period == '3M':
        start_date = end_date - timedelta(days=90)
    elif period == '6M':
        start_date = end_date - timedelta(days=180)
    elif period == '1Y':
        start_date = end_date - timedelta(days=365)
    elif period == 'YTD':
        start_date = datetime(end_date.year, 1, 1)
    else:
        start_date = end_date - timedelta(days=30)
    
    history = portfolio.get_historical_values(start_date, end_date)
    
    return jsonify({
        'dates': [h['date'].strftime('%Y-%m-%d') for h in history],
        'values': [h['value'] for h in history]
    })

@portfolios.route('/load-portfolio')
def load_portfolio():
    success, message = load_portfolio_data()
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('main.index'))


@portfolios.route('/valeurs_suivies')
def valeurs_suivies():
    stocks = Stock.query.order_by(Stock.name.asc()).all()
    return render_template('valeurs_suivies.html', stocks=stocks)

@portfolios.route('/api/stock/<string:symbol>/ichimoku/<string:period>')
def get_ichimoku_data(symbol, period):
    stock = Stock.query.filter_by(symbol=symbol).first_or_404()

    end_date = datetime.now()
    if period == '1M':
        start_date = end_date - timedelta(days=30)
    elif period == '3M':
        start_date = end_date - timedelta(days=90)
    elif period == '6M':
        start_date = end_date - timedelta(days=180)
    elif period == '1Y':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = datetime(end_date.year, 1, 1)  # YTD fallback

    history = StockPriceHistory.query.filter(
    StockPriceHistory.stock_id == stock.id,
    StockPriceHistory.date.between(start_date, end_date)
    ).order_by(StockPriceHistory.date.asc()).all()

    if not history or len(history) < 52:
        return jsonify({'error': 'Not enough data to compute Ichimoku'}), 400

    closes = [h.close_price for h in history]
    highs = [h.high_price for h in history]
    lows = [h.low_price for h in history]
    dates = [h.date.strftime('%Y-%m-%d') for h in history]

    if len(dates) >= 2:
        # intervalle moyen (supposé 1 jour ici)
        last_date = datetime.strptime(dates[-1], "%Y-%m-%d")
        future_dates = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(26)]
        dates += future_dates
    else:
        future_dates = []

    def rolling_max(values, period):
        return [max(values[i - period + 1:i + 1]) if i >= period - 1 else None for i in range(len(values))]

    def rolling_min(values, period):
        return [min(values[i - period + 1:i + 1]) if i >= period - 1 else None for i in range(len(values))]

    def average(a, b):
        return [(x + y) / 2 if x is not None and y is not None else None for x, y in zip(a, b)]

    # Ichimoku calculations
    high_9 = rolling_max(highs, 9)
    low_9 = rolling_min(lows, 9)
    tenkan_sen = average(high_9, low_9)

    high_26 = rolling_max(highs, 26)
    low_26 = rolling_min(lows, 26)
    kijun_sen = average(high_26, low_26)

    senkou_span_a = average(tenkan_sen, kijun_sen)
    senkou_span_a += [None] * 26  # pour combler les dates futures

    high_52 = rolling_max(highs, 52)
    low_52 = rolling_min(lows, 52)
    senkou_span_b = average(high_52, low_52)
    senkou_span_b += [None] * 26  # idem

    chikou_span = [None] * 26 + closes[:-26]

    return jsonify({
        "dates": dates,
        "closePrices": closes,
        "tenkan": tenkan_sen,
        "kijun": kijun_sen,
        "senkouA": senkou_span_a,
        "senkouB": senkou_span_b,
        "chikou": chikou_span
    })

@portfolios.route('/alertes/email')
def envoi_test_email():
    portfolio = Portfolio.query.first()  # à adapter à l’utilisateur courant
    alertes = get_alertes_et_bornes(portfolio)
    envoyer_email_alertes("shakya411@laposte.net", portfolio, alertes)
    return "Email envoyé (si alertes détectées)"

@portfolios.route('/test-alertes-mail')
def test_alertes_mail():
    

    portfolio = Portfolio.query.first()
    alertes = get_alertes_et_bornes(portfolio)
    
    envoyer_email_alertes('shakya411@laposte.net', portfolio, alertes)
    return "Test d’envoi terminé !"

@portfolios.route("/graphique")
def graphique_portefeuille():
    portfolio_id = session.get("selected_portfolio_id")
    selected_portfolio = Portfolio.query.get(portfolio_id) if portfolio_id else None
    return render_template("graphique_portefeuille.html", selected_portfolio=selected_portfolio)

@portfolios.route("/about")
def about():
    """Page À propos de l'application"""
    return render_template("about.html")

@portfolios.route("/api/portefeuille/historique")
def api_historique_portefeuille():
    portfolio_id = session.get("selected_portfolio_id")
    if not portfolio_id:
        return "Aucun portefeuille sélectionné", 400

    portfolio = Portfolio.query.get(portfolio_id)
    if not portfolio:
        return "Portefeuille introuvable", 404
    
    print("/api/portefeuille/historique portefeuille selectionné :", portfolio_id, portfolio.name)
    
    base_path = os.path.join("pea_trading", "static", "exports")

    fichier_valeurs = f"valeurs_portefeuille_journalieres_{portfolio.name}.csv"
    fichier_transactions =  f"transactions_export_{portfolio.name}.csv"
    fichier_cash =  f"cash_mouvements_export_{portfolio.name}.csv"

    print(fichier_transactions)
    print(fichier_valeurs)

    valeurs_path = os.path.join(base_path, fichier_valeurs)
    tx_path = os.path.join(base_path, fichier_transactions)
    cash_path = os.path.join(base_path, fichier_cash)

    df = pd.read_csv(valeurs_path)
    tx = pd.read_csv(tx_path,  parse_dates=["Date"])
    cash = pd.read_csv(cash_path, encoding="ISO-8859-1", parse_dates=["Date"])

    df["date"] = pd.to_datetime(df["date"])
    tx["Date"] = pd.to_datetime(tx["Date"])
    cash["Date"] = pd.to_datetime(cash["Date"])

    result = []
    for _, row in df.iterrows():
        entry = row.to_dict()
        date_obj = row["date"].date()
        print(date_obj)


        # Transactions
        txs = tx[tx["Date"].dt.date == date_obj]
        
        entry["transactions"] = []
        for _, t in txs.iterrows():
            entry["transactions"].append({
                "type": t["Type"].lower(),
                "symbol": t["Symbole"],
                "quantite": t["Quantité"],
                "prix": t["Prix"]
            })
        
        # Debug: log les transactions trouvées
        if len(entry["transactions"]) > 0:
            transactions_info = [f"{t['type']} {t['symbol']}" for t in entry["transactions"]]
            print(f"✅ {len(entry['transactions'])} transaction(s) trouvée(s) pour {date_obj}: {transactions_info}")

        # Versements
        versements = cash[(cash["Date"].dt.date == date_obj) & (cash["Type"].str.lower() == "versement")]
        if not versements.empty:
            v = versements.iloc[0]
            entry["versement"] = {
                "montant": v["Montant"],
                "description": v["Description"]
            }

        # Dividendes
        dividendes = cash[(cash["Date"].dt.date == date_obj) & (cash["Type"].str.lower() == "dividende")]
        if not dividendes.empty:
            d = dividendes.iloc[0]
            entry["dividende"] = {
                "montant": d["Montant"],
                "description": d["Description"]
            }


        result.append(entry)

    #print(result)
    return jsonify(result)

@portfolios.route("/recalculer_valeurs")
def recalculer_valeurs():
    portfolio_id = session.get("selected_portfolio_id")
    if not portfolio_id:
        return "Aucun portefeuille sélectionné", 400

    portfolio = Portfolio.query.get(portfolio_id)
    if not portfolio:
        return "Portefeuille introuvable", 404
    
    print("/recalculer_valeurs portefeuille selectionné :", portfolio_id)

    # Charger données depuis la base
    transactions = Transaction.query.filter_by(portfolio_id=portfolio_id).all()
    cash_movements = CashMovement.query.filter_by(portfolio_id=portfolio_id).all()
    stock_ids = {tx.stock_id for tx in transactions}
    stock_prices = StockPriceHistory.query.filter(StockPriceHistory.stock_id.in_(stock_ids)).all()
    stocks = {s.id: s.symbol for s in Stock.query.filter(Stock.id.in_(stock_ids)).all()}

    # Convertir en DataFrame
    tx_data = pd.DataFrame([{
        "date": t.date,
        "type": t.type.lower(),
        "symbol": t.stock.symbol,
        "quantite": t.quantity,
        "prix": t.price
    } for t in transactions])

    cash_data = pd.DataFrame([{
        "date": c.date,
        "montant": c.amount,
        "type": c.type.lower(),
        "description": c.description
    } for c in cash_movements])

    prix_data = pd.DataFrame([{
        "date": p.date.date(),
        "symbol": stocks.get(p.stock_id),
        "close": p.close_price
    } for p in stock_prices if p.stock_id in stocks])

    if tx_data.empty or prix_data.empty:
        return "Pas assez de données pour générer le fichier."

    tx_data['date'] = pd.to_datetime(tx_data['date'])
    cash_data['date'] = pd.to_datetime(cash_data['date'])
    prix_data['date'] = pd.to_datetime(prix_data['date'])

    start_date = max(tx_data['date'].min(), prix_data['date'].min())
    end_date = prix_data['date'].max()
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

    time_series = []
    for current_date in all_dates:
        prices_today = prix_data[prix_data['date'] == current_date]
        if prices_today.empty:
            continue

        past_tx = tx_data[tx_data['date'] <= current_date].copy()
        past_tx['signed_qty'] = past_tx.apply(
            lambda row: -row['quantite'] if row['type'] == 'vente' else row['quantite'], axis=1)

        positions = past_tx.groupby('symbol').agg({
            'signed_qty': 'sum',
            'prix': 'last'
        }).reset_index()

        price_map = prices_today.set_index('symbol')['close'].to_dict()

        valeur_titres = 0
        for _, row in positions.iterrows():
            qty = row['signed_qty']
            price = price_map.get(row['symbol'])
            if price and qty != 0:
                valeur_titres += qty * price

        past_cash = cash_data[cash_data['date'] <= current_date]
        liquidite = past_cash['montant'].sum()
        total_valeur = valeur_titres + liquidite

        time_series.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "valeur_totale": round(total_valeur, 2),
            "valeur_titres": round(valeur_titres, 2),
            "liquidite": round(liquidite, 2)
        })

    df_final = pd.DataFrame(time_series)
    nom_fichier = f"valeurs_portefeuille_journalieres_{portfolio.name}.csv"
    output_path = os.path.join("pea_trading", "static", "exports", nom_fichier)
    df_final.to_csv(output_path, index=False)
    return f"✅ Recalcul terminé. {len(df_final)} jours générés."
