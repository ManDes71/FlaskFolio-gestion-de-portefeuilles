from pea_trading import app, db
from pea_trading.services.yahoo_finance import update_stock_prices
import threading
from apscheduler.triggers.cron import CronTrigger

import sys
import os

# Force l’affichage immédiat des logs dans Docker
#sys.stdout.reconfigure(line_buffering=True)
#sys.stderr.reconfigure(line_buffering=True)

#print("🧪 TEST STDOUT visible dans les logs ?", flush=True)
#sys.stderr.write("❗TEST STDERR\n")


#python reset_password.py


# http://127.0.0.1:5000/
# docker build --no-cache . -t pea-trading-app
# docker run -p 5000:5000 -v $(pwd)/db_data:/app/db_data pea-trading-app
# --------------------------------
# docker-compose build
# docker-compose up
# docker-compose up --build
#http://localhost:5000/metrics → doit afficher les métriques
#
#http://localhost:9090/targets → flask-app doit être UP
#
#docker-compose down

# 🔹 Prometheus → http://localhost:9090 → Tape flask_http_request_total dans “expression”
#                   dans grafana : http://prometheus:9090

# 🔸 Grafana → http://localhost:3000 (login: admin / toto24 la première fois)

# debug
# docker exec -it pea-trading-app bash
# /app# python app.py


import threading

def start_scheduler_with_jobs():
    try:
        from tasks_scheduler import scheduler_instance, job_alertes, job_update_stocks, job_scraping_intraday

        # ✅ Ajout sécurisé des jobs
        if not scheduler_instance.get_job("job_alertes"):
            scheduler_instance.add_job(job_alertes, trigger="interval", minutes=90, id="job_alertes", misfire_grace_time=300)

        if not scheduler_instance.get_job("job_update_stocks"):
            scheduler_instance.add_job(job_update_stocks, CronTrigger(day_of_week='sat', hour=8), id="job_update_stocks", misfire_grace_time=600)

        if scheduler_instance.get_job("job_scraping_intraday"):
            scheduler_instance.remove_job("job_scraping_intraday")

        # Lundi–vendredi, toutes les 15 min entre 9h30 et 18h30
        scheduler_instance.add_job(
            job_scraping_intraday,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-23',
                minute='*/30',
            ),
            id="job_scraping_intraday",
            misfire_grace_time=300
        )        

        # ✅ Démarrage dans un thread
        scheduler_instance.start()
        print("✅ APScheduler lancé avec jobs : alertes (60s) + MAJ boursière (samedi 8h)")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage du scheduler : {e}")


# 🔁 Protection contre double lancement avec Flask reloader
def is_main_process():
    return os.environ.get("WERKZEUG_RUN_MAIN", "true") == "true"

def launch_background_jobs():
    print("✅ Lancement du thread APScheduler")
    threading.Thread(target=start_scheduler_with_jobs, daemon=True).start()

    if is_main_process():
        print("📈 Mise à jour des prix des actions en cours...")
        with app.app_context():
            try:
                update_stock_prices()
                print("✅ Mise à jour des actions terminée !")
            except Exception as e:
                print(f"❌ Erreur lors de la mise à jour : {str(e)}")


"""
if __name__ == '__main__':
    print("🟢 Lancement de l’application Flask...")

    try:
        print("✅ Lancement du thread APScheduler")
        threading.Thread(target=start_scheduler_with_jobs, daemon=True).start()

    except Exception as e:
        print(f"❌ Erreur lors du démarrage du scheduler : {e}")

    if is_main_process():
        # Mise à jour manuelle une seule fois au démarrage
        print("📈 Mise à jour des prix des actions en cours...")
        with app.app_context():
            try:
                update_stock_prices()
                print("✅ Mise à jour des actions terminée !")
            except Exception as e:
                print(f"❌ Erreur lors de la mise à jour : {str(e)}")

    # 🧠 Important : ne jamais mettre de logique après app.run()
    #app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)
    app.run(debug=False, host='0.0.0.0', port=5000)

    """