# pea_trading/services/notifications.py
from flask_mail import Message
from flask import render_template
from datetime import date
import pandas as pd

def envoyer_email_alertes(user_email, portfolio, alertes, app, mail):
    total = len(alertes["alertes_vente"]) + len(alertes["alertes_achat"])
    if total == 0:
        print("📧 Rien à envoyer")
        return

    subject = f"[Portefeuille] {total} alerte(s) détectée(s)"
    msg = Message(subject, recipients=[user_email])
    msg.body = render_template("emails/alertes.txt", portfolio=portfolio, **alertes)
    msg.html = render_template("emails/alertes.html", portfolio=portfolio, **alertes)

    try:
        with app.app_context():
            mail.send(msg)
        print(f"📤 Email envoyé à {user_email}")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email : {e}")

def is_today_closed():
    try:
        df = pd.read_csv('pea_trading/static/uploads/ClosedDays.csv', encoding='latin1', sep=';')
        df.columns = df.columns.str.strip()  # Nettoie les en-têtes

        if 'Date' not in df.columns:
            raise ValueError(f"Colonne 'Date' absente, colonnes trouvées : {df.columns.tolist()}")

        closed_days = pd.to_datetime(df['Date'], errors='coerce').dropna().dt.date
        return date.today() in closed_days.tolist()
    except Exception as e:
        print(f"Erreur lors de la lecture des jours fériés : {e}")
        return False
