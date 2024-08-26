from .functions import DeallocationSchedular,CheckCounntSchedular
from apscheduler.schedulers.background import BackgroundScheduler


def start_deallocate_schedular():
    """
        This Scheduler Runs at every saturday 10:01 PM in the timezone of 'Asia/Kolkata'
        It deallocates the Expired benches and sends emails for the Allocations expiring next week.
    """
    scheduler = BackgroundScheduler()
    #Runs on every sunday
    scheduler.add_job(DeallocationSchedular,'cron',day_of_week='fri',hour="23",minute="05",timezone='Asia/Kolkata')
    # scheduler.add_job(DeallocationSchedular, 'cron', day_of_week='fri',hour='20',minute="57",timezone='Asia/Kolkata')
    # scheduler.add_job(DeallocationSchedular, 'interval', seconds=60)
    scheduler.start()

def start_count_scheduler():
    """
    This Scheduler Runs every day at 11:05 PM in the timezone of 'Asia/Kolkata'
    It deallocates the Expired benches and sends emails for the Allocations expiring next week.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(CheckCounntSchedular, 'cron', hour=23, minute=30, timezone='Asia/Kolkata')
    # scheduler.add_job(CheckCounntSchedular, 'interval', seconds=30)
    scheduler.start()
    # print(f"{datetime.now()} - APScheduler started successfully.")