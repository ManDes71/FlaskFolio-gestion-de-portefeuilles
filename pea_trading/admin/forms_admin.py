# pea_trading\admin\forms_admin.py
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField, FileField, SelectField, TextAreaField, FloatField, HiddenField, DateField 
from wtforms.validators import DataRequired, NumberRange
from flask_wtf.file import FileAllowed


class ProductForm(FlaskForm):
    symbol = StringField('Symbole', validators=[DataRequired()])
    isin = StringField('ISIN', validators=[DataRequired()])
    name = StringField('Nom', validators=[DataRequired()])
    sector = SelectField('Secteur', choices=[
        ('Technologie', 'Technologie'),
        ('Services de communication', 'Services de communication'),
        ('Consommation discrétionnaire', 'Consommation discrétionnaire'),
        ('Consommation de base', 'Consommation de base'),
        ('Énergie', 'Énergie'),
        ('Services financiers', 'Services financiers'),
        ('Santé', 'Santé'),
        ('Industrie', 'Industrie'),
        ('Matériaux', 'Matériaux'),
        ('Immobilier', 'Immobilier'),
        ('Services publics', 'Services publics')
    ], validators=[DataRequired()])
    date = DateField("Date d'ajout", format='%Y-%m-%d', validators=[DataRequired()])
    quantity = IntegerField('Quantité', validators=[DataRequired(), NumberRange(min=1)])
    purchase_price = DecimalField("Prix d'achat", validators=[DataRequired()])
    max_price = FloatField('Prix max')
    min_price = FloatField('Prix min')
    target_price = FloatField("Objectif de prix")
    submit_add = SubmitField('Ajouter au portefeuille')
    submit_remove = SubmitField('Supprimer du portefeuille')
    submit_reinforce = SubmitField('Renforcer')
    submit_reduce = SubmitField('Alléger')


class RestoreForm(FlaskForm):
    file = FileField('Importer un fichier CSV', validators=[DataRequired(), FileAllowed(['csv'], 'Fichier CSV uniquement!')])
    submit = SubmitField('Restaurer')

class PortfolioSelectionForm(FlaskForm):
    portfolio = SelectField('Sélectionner un portefeuille', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Changer de portefeuille')

class PortfolioCreationForm(FlaskForm):
    name = StringField('Nom du portefeuille', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Créer un portefeuille')


class StockForm(FlaskForm):
    symbol = StringField('Symbole', validators=[DataRequired()])
    isin = StringField('ISIN', validators=[DataRequired()])
    name = StringField('Nom', validators=[DataRequired()])
    sector = SelectField(
    'Secteur',
    choices=[
        ('Technologie', 'Technologie'),
        ('Services de communication', 'Services de communication'),
        ('Consommation discrétionnaire', 'Consommation discrétionnaire'),
        ('Consommation de base', 'Consommation de base'),
        ('Énergie', 'Énergie'),
        ('Services financiers', 'Services financiers'),
        ('Santé', 'Santé'),
        ('Industrie', 'Industrie'),
        ('Matériaux', 'Matériaux'),
        ('Immobilier', 'Immobilier'),
        ('Services publics', 'Services publics')
    ],
    validators=[DataRequired()]
)

    current_price = DecimalField('Prix actuel', validators=[DataRequired()])
    max_price = FloatField('Prix max')
    min_price = FloatField('Prix min')
    target_price = FloatField("Objectif de prix")

class ManualTransactionForm(FlaskForm):
    portfolio_id = HiddenField(validators=[DataRequired()])
    stock_symbol = StringField('Symbole', validators=[DataRequired()])
    quantity = IntegerField('Quantité', validators=[DataRequired(), NumberRange(min=1)])
    price = DecimalField('Prix unitaire', validators=[DataRequired(), NumberRange(min=0)])
    type = SelectField('Type', choices=[('achat', 'Achat'), ('vente', 'Vente')], validators=[DataRequired()])
    date = DateField('Date de la transaction', format='%Y-%m-%d', validators=[DataRequired()]) 
    submit = SubmitField('Enregistrer transaction')

class CashMovementForm(FlaskForm):
    portfolio_id = HiddenField(validators=[DataRequired()])
    amount = DecimalField('Montant', validators=[DataRequired()])
    type = SelectField('Type de mouvement', choices=[
        ('versement', 'Versement'),
        ('retrait', 'Retrait'),
        ('dividende', 'Dividende'),
        ('frais', 'Frais')
    ], validators=[DataRequired()])
    description = StringField('Description')
    date = DateField('Date du mouvement', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Enregistrer mouvement')    

class EditTransactionForm(FlaskForm):
    transaction_id = HiddenField()
    quantity = IntegerField("Quantité", validators=[DataRequired(), NumberRange(min=1)])
    price = DecimalField("Prix unitaire", validators=[DataRequired()])
    description = StringField("Description (optionnel)")
    date = DateField("Date", format="%Y-%m-%d", validators=[DataRequired()])
    submit = SubmitField("Mettre à jour")
