# pea_trading\admin\views_admin.py
from flask import Blueprint, render_template, current_app, redirect, url_for, flash,  session, request, send_file, jsonify, make_response
from pea_trading import db
from flask_mail import Mail
from pea_trading.portfolios.portfolio import Portfolio, Transaction, CashMovement
from pea_trading.portfolios.stock import Stock, Position, StockPriceHistory
from pea_trading.services.yahoo_finance import update_stock_prices, update_historical_prices
from pea_trading.services.finance_ops import ajouter_transaction_et_mouvement, update_transaction_et_cash
from .forms_admin import ProductForm, RestoreForm, PortfolioSelectionForm, PortfolioCreationForm, StockForm, ManualTransactionForm, CashMovementForm, EditTransactionForm
from flask_login import login_required
from pea_trading.services.export_utils import export_stocks_to_csv, export_stock_history_to_csv
from pea_trading.services.export_utils import export_portfolio_positions_to_csv, export_portfolio_transactions_to_csv, export_portfolio_cash_movements_to_csv
from pea_trading.services.import_utils import process_stocks_csv_file, process_stock_history_csv_file
from pea_trading.services.scheduler_jobs import  run_alertes, run_update_stocks,  run_scraping_intraday

from pea_trading.services.scheduler_utils import scheduler_instance
from pea_trading.services.scheduler_utils import start_scheduler_with_jobs
from pea_trading.services.portfolio_loader import restore_portfolio_from_csv
from datetime import datetime
import csv
import pytz
import os
import io
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__)



@admin_bp.route('/admin', methods=['GET', 'POST'])
def admin():
    portfolios = Portfolio.query.all()
    form_portfolio_selection = PortfolioSelectionForm()
    form_portfolio_selection.portfolio.choices = [(p.id, p.name) for p in portfolios]
    form_transaction = ManualTransactionForm()
    form_cash = CashMovementForm()
    form_stock = StockForm()

    selected_portfolio_id = form_portfolio_selection.portfolio.data or request.args.get('portfolio_id')
    if selected_portfolio_id:
        session['selected_portfolio_id'] = selected_portfolio_id
    selected_portfolio = Portfolio.query.get(selected_portfolio_id) if selected_portfolio_id else None
    if selected_portfolio and selected_portfolio.transactions:
        selected_portfolio.transactions.sort(key=lambda t: t.date, reverse=True)


    form = ProductForm()
    form_restore = RestoreForm()
    form_portfolio = PortfolioCreationForm()
    
    if request.method == 'POST':
        form_name = request.form.get("form_name")
        print(form_name)

        if form_name == "portfolio_selection_form":
            return redirect(url_for('admin.admin', portfolio_id=form_portfolio_selection.portfolio.data))
        
        if form_name == "manual_transaction":
            form_transaction.portfolio_id.data = selected_portfolio.id  # ✅ injection
            if form_transaction.validate_on_submit():
                print("etape1")
                stock = Stock.query.filter_by(symbol=form_transaction.stock_symbol.data).first()
                if not stock:
                    flash("Stock introuvable.", "danger")
                else:
                    print("etape2")
                    tx_date = form_transaction.date.data or datetime.now()
                    tx = Transaction(
                        portfolio_id=form_transaction.portfolio_id.data,
                        stock_id=stock.id,
                        quantity=form_transaction.quantity.data,
                        price=form_transaction.price.data,
                        type=form_transaction.type.data,
                        date=tx_date
                    )
                    db.session.add(tx)
                    print("etape3")

                    if tx.type == 'achat':
                        amount = -tx.quantity * tx.price
                    else:
                        amount = tx.quantity * tx.price

                    movement = CashMovement(
                        portfolio_id=tx.portfolio_id,
                        amount=amount,
                        type=tx.type,
                        description=f"{tx.type.capitalize()} manuel(le) de {tx.quantity}x {stock.symbol}",
                        date=tx_date
                    )
                    print("etape4")
                    db.session.add(movement)
                    print("etape5")
                    db.session.commit()
                    flash("Transaction manuelle enregistrée avec succès.", "success")
                return redirect(url_for('admin.admin', portfolio_id=tx.portfolio_id))
            else:
                print("❌ Le formulaire n'est pas valide.")
                flash("Le formulaire n'est pas valide.", "danger")
                print(form_transaction.errors)
        
        if form_name == "cash_movement" :
            print("cash_movement")
            form_cash.portfolio_id.data = selected_portfolio.id  # ✅ injection
            if form_cash.validate_on_submit():
                movement = CashMovement(
                    portfolio_id=form_cash.portfolio_id.data,
                    amount=form_cash.amount.data,
                    type=form_cash.type.data,
                    description=form_cash.description.data,
                    date=form_cash.date.data 
                )
                db.session.add(movement)
                db.session.commit()
                flash("Mouvement de trésorerie enregistré avec succès.", "success")
                return redirect(url_for('admin.admin', portfolio_id=form_cash.portfolio_id.data))
            else:
                print("❌ Le formulaire n'est pas valide.")
                flash("Le formulaire n'est pas valide.", "danger")
                print(form_cash.errors)

        if form_name == "restore_form":
            file = form_restore.file.data
            if file:
                from werkzeug.utils import secure_filename
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.root_path, 'static', 'uploads', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                print(f"📥 Fichier CSV uploadé : {filepath}")

                try:
                    nb = restore_portfolio_from_csv(filepath, selected_portfolio)
                    flash(f"{nb} lignes restaurées avec succès.", "success")
                except Exception as e:
                    flash(f"Erreur lors de la restauration : {str(e)}", "danger")

                return redirect(url_for('admin.admin', portfolio_id=selected_portfolio.id))
        
        
        if form.submit_remove.data:
            stock = Stock.query.filter_by(symbol=form.symbol.data).first()
            if stock:
                position = Position.query.filter_by(
                    portfolio_id=selected_portfolio.id,
                    stock_id=stock.id
                ).first()
                if position:
                    # On simule une vente totale au prix d’achat (ou mieux : prix actuel si dispo)
                    transaction_date = form.date.data or datetime.now().date()
                    try:
                        sell_price = float(form.purchase_price.data)
                    except (ValueError, TypeError):
                        sell_price = stock.current_price or position.purchase_price
                    quantity = position.quantity

                    ajouter_transaction_et_mouvement(
                        portfolio_id=selected_portfolio.id,
                        stock_id=stock.id,
                        quantity=quantity,
                        price=sell_price,
                        type_op="vente",
                        description=f"Vente complète de {quantity}x {stock.symbol} (suppression)",
                        date=transaction_date
                    )

                    db.session.delete(position)
                    db.session.commit()
                    flash(f'Valeur {stock.symbol} vendue et supprimée du portefeuille.', 'success')
                else:
                    flash("Cette valeur n'est pas présente dans ce portefeuille.", 'warning')
            else:
                flash('Aucune valeur trouvée avec ce symbole.', 'danger')
            return redirect(url_for('admin.admin', portfolio_id=selected_portfolio.id))

        
       
    
    return render_template('admin.html', portfolios=portfolios,
                            selected_portfolio=selected_portfolio,
                              form=form, form_restore=form_restore,
                                form_portfolio_selection=form_portfolio_selection,
                                form_portfolio_creation=form_portfolio,
                                form_transaction=form_transaction, 
                                form_cash=form_cash,
								form_stock=form_stock)

@admin_bp.route('/create_portfolio', methods=['POST'])
def create_portfolio():
    form = PortfolioCreationForm()
    if form.validate_on_submit():
        new_portfolio = Portfolio(
            name=form.name.data,
            description=form.description.data,
            created_at=datetime.now(),
            user_id=1  # À changer dynamiquement selon l'utilisateur connecté
        )
        db.session.add(new_portfolio)
        db.session.commit()
        flash('Portefeuille créé avec succès.', 'success')
    else:
        flash('Erreur dans la création du portefeuille.', 'danger')
    return redirect(url_for('admin.admin'))

@admin_bp.route('/admin/add_product', methods=['POST'])
def add_product():
    print("entree add product")
    form = ProductForm()
    portfolio_id = request.form.get("portfolio_id")
    selected_portfolio = Portfolio.query.get(portfolio_id)

    if not selected_portfolio:
        return jsonify({"success": False, "message": "Portefeuille non trouvé."}), 400

    if form.validate_on_submit():
        stock = Stock.query.filter_by(symbol=form.symbol.data).first()
        if not stock:
            stock = Stock(
                symbol=form.symbol.data,
                isin=form.isin.data,
                name=form.name.data,
                sector=form.sector.data,
                current_price=0.0,
                last_updated=datetime.now(),
                max_price=form.max_price.data,
                min_price=form.min_price.data,
                target_price=form.target_price.data
            )
            db.session.add(stock)
            db.session.flush()

        position = Position.query.filter_by(
            portfolio_id=selected_portfolio.id,
            stock_id=stock.id
        ).first()

        quantity = form.quantity.data
        price = form.purchase_price.data

        # ⚙️ Détection de l'action demandée
        if 'submit_reinforce' in request.form:
            action_type = "renforcer"
        elif 'submit_reduce' in request.form:
            action_type = "alleger"
        else:
            action_type = "ajouter"

        print(action_type)


        if action_type == "renforcer":
            print("renforcer")
            if not position:
                return jsonify({"success": False, "message": "Position inexistante pour renforcer."}), 400
            total_quantity = position.quantity + quantity
            position.purchase_price = (
                float(position.purchase_price) * position.quantity + float(price) * quantity
                ) / total_quantity
            position.quantity = total_quantity

            ajouter_transaction_et_mouvement(
                portfolio_id=selected_portfolio.id,
                stock_id=stock.id,
                quantity=quantity,
                price=price,
                type_op="achat",
                description=f"Renforcement : achat de {quantity}x {stock.symbol}",
                date=form.date.data 
            )

        elif action_type == "alleger":
            print("alleger")
            if not position:
                return jsonify({"success": False, "message": "Position inexistante pour alléger."}), 400
            if quantity > position.quantity:
                return jsonify({"success": False, "message": "Quantité à vendre supérieure à la position."}), 400
            position.quantity -= quantity

            ajouter_transaction_et_mouvement(
                portfolio_id=selected_portfolio.id,
                stock_id=stock.id,
                quantity=quantity,
                price = price,
                type_op="vente",
                description=f"Allègement : vente de {quantity}x {stock.symbol}",
                 date=form.date.data 
            )

            if position.quantity == 0:
                db.session.delete(position)

        else:  # action_type == "ajouter"
            print("ajouter")
            if position:
                return jsonify({"success": False, "message": "Position déjà existante."}), 400
            else:
                position = Position(
                    portfolio_id=selected_portfolio.id,
                    stock_id=stock.id,
                    quantity=quantity,
                    purchase_price=price,
                    purchase_date=form.date.data 
                )
                db.session.add(position)
            ajouter_transaction_et_mouvement(
                portfolio_id=selected_portfolio.id,
                stock_id=stock.id,
                quantity=quantity,
                price=price,
                type_op="achat",
                description=f"Achat de {quantity} {stock.symbol}",
                date=form.date.data 
            )

        db.session.commit()

        if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
            print("ok1")
            return jsonify({"success": True, "message": f"Action '{action_type}' réalisée avec succès."})
        else:
            print("ok2")
            flash(f"{action_type.capitalize()} réalisé avec succès.", "success")
            return redirect(url_for('admin.admin', portfolio_id=selected_portfolio.id))
    else:
        print("📛 Erreurs formulaire ProductForm:", form.errors)
    # Erreur
    if request.accept_mimetypes['application/json'] >= request.accept_mimetypes['text/html']:
        print("KO1")
        return jsonify({"success": False, "errors": form.errors}), 400
    else:
        print("KO2")
        flash("Erreur dans le formulaire.", "danger")
        return redirect(url_for('admin.admin', portfolio_id=selected_portfolio.id))


@admin_bp.route('/admin/export_csv')
def export_csv():
    
    portfolio_id = request.args.get('portfolio_id', None)

    if not portfolio_id:
        flash("Veuillez sélectionner un portefeuille.", "danger")
        return redirect(url_for('admin.admin'))

    portfolio = Portfolio.query.get(portfolio_id)
    if not portfolio:
        flash("Portefeuille non trouvé.", "danger")
        return redirect(url_for('admin.admin'))

    # Générer un nom de fichier unique pour le portefeuille
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"portefeuille_export_{portfolio.name.replace(' ', '_')}_{timestamp}.csv"
    
    try:
        filepath = export_portfolio_positions_to_csv(portfolio, filename)

        if not os.path.exists(filepath):
            print(f"⚠️ Erreur : le fichier {filepath} n'a pas été créé !")
            flash("Erreur lors de la génération du fichier.", "danger")
            return redirect(url_for("admin.admin", portfolio_id=portfolio.id))

        return redirect(url_for('static', filename=f'exports/{filename}'))

    except Exception as e:
        flash(f"Erreur lors de l'exportation: {str(e)}", "danger")
        return redirect(url_for("admin.admin", portfolio_id=portfolio.id))
    
@admin_bp.route("/admin/restore_positions", methods=["POST"])
@login_required
def restore_positions():
    form = RestoreForm()
    if form.validate_on_submit():
        file = form.file.data
        portfolio_id = request.form.get("portfolio_id")
        portfolio = Portfolio.query.get(portfolio_id)

        if not portfolio:
            flash("❌ Portefeuille non trouvé", "danger")
            return redirect(url_for("admin.admin"))

        # Sauvegarde temporaire
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.root_path, "static", "uploads", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)

        # Importer via utilitaire
        from pea_trading.services.import_utils import process_portfolio_positions_csv
        success, message = process_portfolio_positions_csv(portfolio.name, filename)

        if success:
            flash(f"✅ {message}", "success")
        else:
            flash(f"❌ Erreur pendant l'import : {message}", "danger")

        return redirect(url_for("admin.admin", portfolio_id=portfolio.id))

    flash("❌ Formulaire invalide ou fichier manquant", "danger")
    return redirect(url_for("admin.admin"))

    
@admin_bp.route('/admin/export_stocks')
def export_stocks():
    filename = 'stocks_export.csv'
    filepath = export_stocks_to_csv(filename)
    return send_file(filepath, as_attachment=True)


@admin_bp.route('/admin/valeurs', methods=['GET'])
def admin_valeurs():
    stocks = Stock.query.order_by(Stock.name.asc()).all()  # Récupérer toutes les actions de la table Stock
    return render_template('admin_valeurs.html', stocks=stocks)


@admin_bp.route('/admin/valeurs/edit/<int:stock_id>', methods=['GET', 'POST'])
def edit_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    form = StockForm(obj=stock)  # Pré-remplit le formulaire avec les données existantes

    if form.validate_on_submit():
        stock.symbol = form.symbol.data
        stock.isin = form.isin.data
        stock.name = form.name.data
        stock.sector = form.sector.data
        stock.current_price = form.current_price.data
        stock.max_price = form.max_price.data
        stock.min_price = form.min_price.data
        stock.target_price = form.target_price.data

        db.session.commit()
        flash("Stock modifié avec succès !", "success")
        return redirect(url_for('admin.admin_valeurs'))

    return render_template('edit_stock.html', form=form, stock=stock)

@admin_bp.route('/admin/valeurs/delete/<int:stock_id>', methods=['POST'])
def delete_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)

    # Supprimer les historiques liés à l'action
    StockPriceHistory.query.filter_by(stock_id=stock.id).delete()

    # Supprimer les positions liées (optionnel si pas de contrainte ON DELETE CASCADE)
    Position.query.filter_by(stock_id=stock.id).delete()

    db.session.delete(stock)
    db.session.commit()
    flash("Stock supprimé avec succès !", "success")
    return redirect(url_for('admin.admin_valeurs'))

@admin_bp.route('/admin/export_stock_history')
def export_stock_history():
    filename = 'historique_stocks.csv'
    filepath = export_stock_history_to_csv(filename)
    return send_file(filepath, as_attachment=True)



@admin_bp.route('/admin/import_stocks_csv', methods=['POST'])
def import_stocks_csv():
    if 'stocks_file' not in request.files or request.files['stocks_file'].filename == '':
        flash('Aucun fichier sélectionné.', 'danger')
        return redirect(url_for('admin.admin'))

    file = request.files['stocks_file']
    filepath = os.path.join(current_app.root_path,'static', 'uploads', secure_filename(file.filename))
    file.save(filepath)

    success, error = process_stocks_csv_file(filepath)
    if success:
        flash('Importation des actions réussie.', 'success')
    else:
        flash(f'Erreur lors de l\'importation: {error}', 'danger')
    return redirect(url_for('admin.admin'))


@admin_bp.route('/admin/import_stock_history_csv', methods=['POST'])
def import_stock_history_csv():
    if 'history_file' not in request.files:
        flash('Aucun fichier sélectionné.', 'danger')
        return redirect(url_for('admin.admin'))

    file = request.files['history_file']
    if file.filename == '':
        flash('Fichier invalide.', 'danger')
        return redirect(url_for('admin.admin'))

    filename = secure_filename(file.filename)
    filepath = os.path.join('uploads', file.filename)
    file.save(filepath)

    print(f"📥 Fichier CSV d’historique reçu : {filepath}")

    success, result = process_stock_history_csv_file(filename)
    if success:
        flash(f"✅ {result} lignes importées avec succès depuis {filename}.", "success")
    else:
        flash(f"❌ Erreur lors de l’importation : {result}", "danger")

    return redirect(url_for('admin.admin'))


@admin_bp.route('/admin/update_stocks', methods=['POST'])
def update_stocks_manual():
    try:
        update_stock_prices()
        update_historical_prices()
        flash("✅ Mise à jour des valeurs réussie !", "success")
    except Exception as e:
        flash(f"❌ Erreur lors de la mise à jour : {str(e)}", "danger")
    return redirect(url_for('admin.admin'))

# export CSV des transactions ou liquidités d’un portefeuille sélectionné

@admin_bp.route('/admin/export_transactions')
def export_transactions():
    portfolio_id = request.args.get("portfolio_id")
    if not portfolio_id:
        flash("Aucun portefeuille sélectionné.", "danger")
        return redirect(url_for('admin.admin'))

    portfolio = Portfolio.query.get(portfolio_id)
    if not portfolio:
        flash("Portefeuille introuvable.", "danger")
        return redirect(url_for('admin.admin'))
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transactions_{portfolio.name.replace(' ', '_')}_{timestamp}.csv"
    
    try:
        filepath = export_portfolio_transactions_to_csv(portfolio, filename)

        if not os.path.exists(filepath):
            print(f"⚠️ Erreur : le fichier {filepath} n'a pas été créé !")
            flash("Erreur lors de la génération du fichier.", "danger")
            return redirect(url_for("admin.admin", portfolio_id=portfolio.id))

        flash("Export des transactions réussi.", "success")
        return redirect(url_for('static', filename=f'exports/{filename}'))

    except Exception as e:
        flash(f"Erreur lors de l'exportation: {str(e)}", "danger")
        return redirect(url_for("admin.admin", portfolio_id=portfolio.id))
    


@admin_bp.route('/admin/export_cash_movements')
def export_cash_movements():
    portfolio_id = request.args.get("portfolio_id")
    if not portfolio_id:
        flash("Aucun portefeuille sélectionné.", "danger")
        return redirect(url_for('admin.admin'))
    
    portfolio = Portfolio.query.get(portfolio_id)
    if not portfolio:
        flash("Portefeuille introuvable.", "danger")
        return redirect(url_for('admin.admin'))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cash_mouvements_{portfolio.name.replace(' ', '_')}_{timestamp}.csv"
    
    try:
        filepath = export_portfolio_cash_movements_to_csv(portfolio, filename)

        if not os.path.exists(filepath):
            print(f"⚠️ Erreur : le fichier {filepath} n'a pas été créé !")
            flash("Erreur lors de la génération du fichier.", "danger")
            return redirect(url_for("admin.admin", portfolio_id=portfolio.id))

        flash("Export des mouvements de trésorerie réussi.", "success")
        return redirect(url_for('static', filename=f'exports/{filename}'))

    except Exception as e:
        flash(f"Erreur lors de l'exportation: {str(e)}", "danger")
        return redirect(url_for("admin.admin", portfolio_id=portfolio.id))

    

@admin_bp.route("/admin/edit_transaction/<int:transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    form = EditTransactionForm(obj=transaction)

    if form.validate_on_submit():
        update_transaction_et_cash(
            transaction_id=transaction.id,
            new_quantity=form.quantity.data,
            new_price=form.price.data,
            new_description=form.description.data,
            new_date=form.date.data 
        )
        flash("Transaction mise à jour avec succès ✅", "success")
        return redirect(url_for('admin.admin', portfolio_id=transaction.portfolio_id))
    
    if request.method == "GET":
        form.date.data = transaction.date

    return render_template("edit_transaction.html", form=form, transaction=transaction)

@admin_bp.route('/admin/delete_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    # Trouver le mouvement de cash correspondant
    mouvement = CashMovement.query.filter_by(
        portfolio_id=transaction.portfolio_id,
        date=transaction.date,
        amount=(transaction.price * transaction.quantity) * (-1 if transaction.type == 'achat' else 1)
    ).first()

    try:
        db.session.delete(transaction)
        if mouvement:
            db.session.delete(mouvement)
        db.session.commit()
        flash("Transaction supprimée avec succès ✅", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")

    return redirect(url_for('admin.admin', portfolio_id=transaction.portfolio_id))

@admin_bp.route('/admin/delete_cash_movement/<int:movement_id>', methods=['POST'])
@login_required
def delete_cash_movement(movement_id):
    movement = CashMovement.query.get_or_404(movement_id)
    db.session.delete(movement)
    db.session.commit()
    flash("Mouvement supprimé ✅", "success")
    return redirect(request.referrer or url_for('admin.admin'))

# afficher les transactions et liquidités de manière publique, avec pagination

@admin_bp.route("/transactions")
def all_transactions():
    page = request.args.get('page', 1, type=int)
    selected_portfolio_id = request.args.get('portfolio_id', type=int)

    portfolios = Portfolio.query.all()
    query = Transaction.query.order_by(Transaction.date.desc())
    if selected_portfolio_id:
        query = query.filter_by(portfolio_id=selected_portfolio_id)

    transactions = query.paginate(page=page, per_page=20)
    return render_template("transactions.html", transactions=transactions, portfolios=portfolios, selected_portfolio_id=selected_portfolio_id)


@admin_bp.route("/liquidites")
def all_cash_movements():
    page = request.args.get('page', 1, type=int)
    selected_portfolio_id = request.args.get('portfolio_id', type=int)

    portfolios = Portfolio.query.all()
    query = CashMovement.query.order_by(CashMovement.date.desc())
    if selected_portfolio_id:
        query = query.filter_by(portfolio_id=selected_portfolio_id)

    movements = query.paginate(page=page, per_page=20)
    return render_template("liquidites.html", movements=movements, portfolios=portfolios, selected_portfolio_id=selected_portfolio_id)

# affichage admin des transactions et mouvements de trésorerie
@admin_bp.route("/admin/transactions")
@login_required
def admin_transactions():
    page = request.args.get('page', 1, type=int)
    selected_portfolio_id = request.args.get('portfolio_id', type=int)

    portfolios = Portfolio.query.all()
    query = Transaction.query.order_by(Transaction.date.desc())
    if selected_portfolio_id:
        query = query.filter_by(portfolio_id=selected_portfolio_id)

    transactions = query.paginate(page=page, per_page=30)
    return render_template("admin_transactions.html", transactions=transactions, portfolios=portfolios, selected_portfolio_id=selected_portfolio_id)

@admin_bp.route("/admin/liquidites")
@login_required
def admin_liquidites():
    page = request.args.get('page', 1, type=int)
    selected_portfolio_id = request.args.get('portfolio_id', type=int)

    portfolios = Portfolio.query.all()
    query = CashMovement.query.order_by(CashMovement.date.desc())
    if selected_portfolio_id:
        query = query.filter_by(portfolio_id=selected_portfolio_id)

    movements = query.paginate(page=page, per_page=30)
    return render_template("admin_liquidites.html", movements=movements, portfolios=portfolios, selected_portfolio_id=selected_portfolio_id)

# export CSV des transactions ou liquidités d’un portefeuille sélectionné
"""
@admin_bp.route('/admin/export_transactions')
@login_required
def export_transactions_csv():
    portfolio_id = request.args.get('portfolio_id', type=int)
    query = Transaction.query
    if portfolio_id:
        query = query.filter_by(portfolio_id=portfolio_id)

    transactions = query.order_by(Transaction.date.desc()).all()

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["Date", "Type", "Symbole", "Quantité", "Prix", "Montant"])
    for tx in transactions:
        writer.writerow([tx.date, tx.type, tx.stock.symbol, tx.quantity, tx.price, tx.quantity * tx.price])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=transactions.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@admin_bp.route('/admin/export_liquidites')
@login_required
def export_cash_movements_csv():
    portfolio_id = request.args.get('portfolio_id', type=int)
    query = CashMovement.query
    if portfolio_id:
        query = query.filter_by(portfolio_id=portfolio_id)

    movements = query.order_by(CashMovement.date.desc()).all()

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["Date", "Type", "Montant", "Description"])
    for mv in movements:
        writer.writerow([mv.date, mv.type, mv.amount, mv.description])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=liquidites.csv"
    output.headers["Content-type"] = "text/csv"
    return output
    
"""

@admin_bp.route('/export/transactions')
@login_required
def export_public_transactions_csv():
    portfolio_id = request.args.get('portfolio_id', type=int)
    query = Transaction.query
    if portfolio_id:
        query = query.filter_by(portfolio_id=portfolio_id)
    transactions = query.order_by(Transaction.date.desc()).all()

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["Date", "Type", "Symbole", "Quantité", "Prix", "Montant"])
    for tx in transactions:
        writer.writerow([tx.date, tx.type, tx.stock.symbol, tx.quantity, tx.price, tx.quantity * tx.price])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=transactions.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@admin_bp.route('/export/liquidites')
@login_required
def export_public_cash_csv():
    portfolio_id = request.args.get('portfolio_id', type=int)
    query = CashMovement.query
    if portfolio_id:
        query = query.filter_by(portfolio_id=portfolio_id)
    movements = query.order_by(CashMovement.date.desc()).all()

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["Date", "Type", "Montant", "Description"])
    for mv in movements:
        writer.writerow([mv.date, mv.type, mv.amount, mv.description])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=liquidites.csv"
    output.headers["Content-type"] = "text/csv"
    return output



@admin_bp.route('/admin/fill_stock_info', methods=['POST'])
def fill_stock_info():
    symbol = request.form.get('symbol')
    if not symbol:
        return jsonify({'success': False, 'message': 'Aucun symbole fourni'})

    stock = Stock.query.filter(
        (Stock.symbol == symbol.upper()) |
        (Stock.symbol == symbol.upper().replace('.PA', '')) |
        (Stock.symbol == symbol)
    ).first()

    SECTOR_MAPPING = {
    'Services aux collectivités': 'Services publics',
    'Consommation discrétionnaire': 'Consommation discrétionnaire',
    'Matériaux': 'Matériaux',
    'Industrie': 'Industrie',
    'Technologie': 'Technologie',
    'Santé': 'Santé',
    'Services de communication': 'Services de communication',
    'Consommation de base':'Consommation de base',
    'Énergie': 'Énergie',
    'Services financiers': 'Services financiers',
    'Immobilier':'Immobilier'
    }

    sector_clean = SECTOR_MAPPING.get(stock.sector, stock.sector)


    if stock:
        return jsonify({
            'success': True,
            'isin': stock.isin,
            'name': stock.name,
            'sector': sector_clean,
            'current_price': stock.current_price,
            'max_price': stock.max_price,
            'min_price': stock.min_price,
            'target_price': stock.target_price
        })
    else:
        return jsonify({'success': False, 'message': f'Symbole "{symbol}" non trouvé en base'})

@admin_bp.route('/admin/add_stock', methods=['POST'])
def add_stock():
    form = StockForm()
    if form.validate_on_submit():
        print(f"🔍 Tentative d'ajout de : {form.symbol.data}")
        stock_existant = Stock.query.filter_by(symbol=form.symbol.data).first()
        if stock_existant:
            print(f"⚠️ Action déjà existante : {stock_existant}")
            flash("Cette valeur existe déjà.", "warning")
            return redirect(url_for('admin.admin'))


        new_stock = Stock(
            symbol=form.symbol.data,
            isin=form.isin.data,
            name=form.name.data,
            sector=form.sector.data,
            current_price=form.current_price.data,
            max_price=form.max_price.data,
            min_price=form.min_price.data,
            target_price=form.target_price.data,
            last_updated=datetime.now()
        )
        db.session.add(new_stock)
        db.session.commit()
        flash("Nouvelle valeur ajoutée avec succès !", "success")
    else:
        flash("Erreur dans le formulaire d'ajout de valeur.", "danger")
    return redirect(url_for('admin.admin'))
    

@admin_bp.route('/admin/scheduler')
@login_required
def scheduler_dashboard():
    jobs = scheduler_instance.get_jobs()
    print("🔍 Jobs enregistrés dans le scheduler :")
    for job in jobs:
        print(f"- {job.id}: next_run={job.next_run_time}, trigger={job.trigger}, func={job.func}")

    server_time = datetime.now()  # Heure actuelle du serveur (locale à l'OS du serveur)

    # Heure de Paris
    paris_tz = pytz.timezone('Europe/Paris')
    paris_time = datetime.now(paris_tz)

    # Créer une liste enrichie manuellement
    enriched_jobs = []
    for job in jobs:
        enriched_jobs.append({
            "id": job.id,
            "func_ref": job.func_ref,
            "trigger_class": job.trigger.__class__.__name__,
            "trigger": str(job.trigger),
            "next_run_time_server": job.next_run_time,
            "next_run_time_paris": job.next_run_time.astimezone(paris_tz) if job.next_run_time else None
        })  


    return render_template('admin_scheduler.html', jobs=enriched_jobs,  server_time=server_time, paris_time=paris_time)

@admin_bp.route('/admin/scheduler/run/<job_id>', methods=['POST'])
@login_required
def run_scheduler_job_now(job_id):
    try:
        if job_id == "job_alertes":
            run_alertes()
            flash("🔔 Job d'alertes lancé avec succès", "success")
        elif job_id == "job_update_stocks":
            run_update_stocks()
            flash("📈 Mise à jour des cours lancée avec succès", "success")
        elif job_id == "job_scraping_intraday":
            run_scraping_intraday()
            flash("⚡ Scraping intraday lancé avec succès", "success")
        else:
            flash(f"❌ Job inconnu : {job_id}", "danger")
    except Exception as e:
        flash(f"❌ Erreur lors de l'exécution de la tâche : {str(e)}", "danger")
    
    return redirect(url_for('admin.scheduler_dashboard'))


@admin_bp.route('/admin/scheduler/pause/<job_id>', methods=['POST'])
@login_required
def pause_scheduler_job(job_id):
    job = scheduler_instance.get_job(job_id)
    if job:
        try:
            scheduler_instance.pause_job(job_id)
            flash(f"⏸ Tâche '{job_id}' mise en pause.", "warning")
        except Exception as e:
            flash(f"❌ Erreur lors de la mise en pause : {str(e)}", "danger")
    else:
        flash("❌ Tâche introuvable.", "danger")
    return redirect(url_for('admin.scheduler_dashboard'))

@admin_bp.route('/admin/scheduler/remove/<job_id>', methods=['POST'])
@login_required
def remove_scheduler_job(job_id):
    job = scheduler_instance.get_job(job_id)
    if job:
        try:
            scheduler_instance.remove_job(job_id)
            flash(f"🗑 Tâche '{job_id}' supprimée.", "danger")
        except Exception as e:
            flash(f"❌ Erreur lors de la suppression : {str(e)}", "danger")
    else:
        flash("❌ Tâche introuvable.", "danger")
    return redirect(url_for('admin.scheduler_dashboard'))

@admin_bp.route('/admin/restart_scheduler', methods=['POST'])
@login_required
def restart_scheduler():
    try:
        app = current_app._get_current_object()
        mail = Mail(app)
        start_scheduler_with_jobs(app, db, mail)
        flash('✅ Scheduler relancé avec succès.', 'success')
    except Exception as e:
        flash(f'❌ Erreur : {e}', 'danger')
    return redirect(url_for('admin.scheduler_dashboard'))


from pea_trading.users.models import User
from werkzeug.security import generate_password_hash

@admin_bp.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
    users = User.query.all()

    if request.method == 'POST':
        user_id = request.form.get("user_id")
        new_password = request.form.get("new_password")

        if not user_id or not new_password:
            flash("❌ Tous les champs sont obligatoires.", "danger")
        else:
            user = User.query.get(user_id)
            if user:
                user.password_hash = generate_password_hash(new_password)
                db.session.commit()
                flash(f"✅ Mot de passe réinitialisé pour {user.username}.", "success")
            else:
                flash("❌ Utilisateur introuvable.", "danger")

        return redirect(url_for('admin.admin_users'))

    return render_template("admin_users.html", users=users)

