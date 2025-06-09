from apscheduler.triggers.cron import CronTrigger
#from apscheduler.schedulers.background import BackgroundScheduler
from tasks_scheduler import scheduler_instance, job_alertes, job_update_stocks, job_scraping_intraday
import pytz
paris_tz = pytz.timezone('Europe/Paris')

#scheduler = BackgroundScheduler()

def start_scheduler_with_jobs():
    try:
        

        if scheduler_instance.running:
            print("♻️ Scheduler déjà actif, arrêt et nettoyage...")
            scheduler_instance.remove_all_jobs()
            scheduler_instance.shutdown(wait=False)

        print("🚀 Démarrage du scheduler avec nouveaux jobs...")


        # Lundi–vendredi, toutes les 10 min entre 9h et 18h
        scheduler_instance.add_job(
            job_alertes,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-18',
                minute='*/50',
                timezone=paris_tz 
            ),
            id="job_alertes",
            misfire_grace_time=300
        )

        if not scheduler_instance.get_job("job_update_stocks"):
            scheduler_instance.add_job(job_update_stocks, 
                CronTrigger(day_of_week='sat', hour=8,timezone=paris_tz ), id="job_update_stocks", misfire_grace_time=600)

        if scheduler_instance.get_job("job_scraping_intraday"):
            scheduler_instance.remove_job("job_scraping_intraday")

        # Lundi–vendredi, toutes les 15 min entre 9h30 et 18h30
        scheduler_instance.add_job(
            job_scraping_intraday,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-18',
                minute='*/30',
                timezone=paris_tz 
            ),
            id="job_scraping_intraday",
            misfire_grace_time=300
        )        

        # ✅ Démarrage dans un thread
        scheduler_instance.start()
        print("✅ APScheduler lancé avec jobs : alertes (60s) + MAJ boursière (samedi 8h)")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage du scheduler : {e}")
        raise
