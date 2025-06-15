from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from .scheduler_jobs import register_jobs
import pytz
paris_tz = pytz.timezone('Europe/Paris')

scheduler_instance = BackgroundScheduler()

def start_scheduler_with_jobs(app, db, mail):
    if scheduler_instance.running:
        scheduler_instance.remove_all_jobs()
        scheduler_instance.shutdown(wait=False)
    
    print("🚀 Démarrage du scheduler...")
    register_jobs(scheduler_instance, app, mail, db)
    scheduler_instance.start()
    print("✅ Scheduler prêt.")