from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import logging

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logging.info("Scheduler started")

    def add_one_off_task(self, task_id: str, run_date: datetime, callback, args=None):
        if args is None:
            args = []
        try:
            self.scheduler.add_job(
                callback,
                DateTrigger(run_date=run_date),
                id=task_id,
                args=args,
                replace_existing=True
            )
            logging.info(f"Scheduled task {task_id} at {run_date}")
        except Exception as e:
            logging.error(f"Error scheduling task {task_id}: {e}")

    def add_countdown_task(self, task_id: str, minutes: int, callback, args=None):
        run_date = datetime.now() + timedelta(minutes=minutes)
        self.add_one_off_task(task_id, run_date, callback, args)

    def remove_task(self, task_id: str):
        try:
            self.scheduler.remove_job(task_id)
            logging.info(f"Removed task {task_id}")
        except Exception:
            pass # Job might not exist

    def shutdown(self):
        self.scheduler.shutdown()
