"""
Reminder Scheduler for DutyBot
Handles scheduling and sending reminder notifications
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
import asyncio

logger = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("⏰ Reminder scheduler initialized and started")

    def schedule_reminder(
        self,
        application,
        user_id: int,
        task_id: int,
        task_title: str,
        remind_at: datetime,
        task_time: str,
    ):
        """Schedule a one-time reminder for a specific task."""
        if remind_at <= datetime.now():
            logger.warning(f"Reminder time {remind_at} is in the past, skipping")
            return

        job_id = f"reminder_{user_id}_{task_id}"

        async def send_reminder():
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🔔 *Reminder!*\n\n"
                        f"📌 *{task_title}*\n"
                        f"🕐 Scheduled at: *{task_time}*\n\n"
                        f"_Your task is coming up soon!_"
                    ),
                    parse_mode="Markdown"
                )
                logger.info(f"Sent reminder for task {task_id} to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send reminder: {e}")

        def sync_wrapper():
            """Wrapper to run async function in the application's event loop"""
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(send_reminder())
                else:
                    loop.run_until_complete(send_reminder())
            except Exception as e:
                logger.error(f"Error in reminder wrapper: {e}")

        self.scheduler.add_job(
            sync_wrapper,
            trigger=DateTrigger(run_date=remind_at),
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info(f"Scheduled reminder: job={job_id} at={remind_at}")

    def cancel_reminder(self, user_id: int, task_id: int):
        """Cancel a scheduled reminder."""
        job_id = f"reminder_{user_id}_{task_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Cancelled reminder {job_id}")
        except Exception:
            pass  # Job may not exist

    def schedule_daily_summary(self, application, user_id: int, hour: int = 8, minute: int = 0):
        """Schedule daily morning summary at given hour."""
        from database import Database
        db = Database()
        
        job_id = f"daily_summary_{user_id}"

        async def send_daily_summary():
            from datetime import date
            today = date.today().strftime("%Y-%m-%d")
            tasks = db.get_tasks_by_date(user_id, today)
            if not tasks:
                return
            
            total = len(tasks)
            done = sum(1 for t in tasks if t["completed"])
            
            text = f"🌅 *Good morning! Today's Duties*\n\n"
            text += f"📊 {done}/{total} completed\n\n"
            
            for t in tasks:
                status = "✅" if t["completed"] else "⬜"
                text += f"{status} {t['title']} `[{t['task_time']}]`\n"
            
            text += "\n_Have a productive day!_ 💪"
            
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to send daily summary: {e}")

        self.scheduler.add_job(
            send_daily_summary,
            trigger=IntervalTrigger(days=1, start_date=f"2024-01-01 {hour:02d}:{minute:02d}:00"),
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Scheduled daily summary for user {user_id} at {hour:02d}:{minute:02d}")

    def restore_reminders(self, application, db):
        """Restore all pending reminders from DB on bot restart."""
        from datetime import date as dt
        from datetime import timedelta
        
        today = dt.today().strftime("%Y-%m-%d")
        
        # Get all users
        with db.get_conn() as conn:
            users = conn.execute("SELECT user_id FROM users").fetchall()
        
        total_restored = 0
        for user_row in users:
            uid = user_row["user_id"]
            tasks = db.get_upcoming_tasks_with_reminders(uid)
            for task in tasks:
                try:
                    task_dt = datetime.strptime(
                        f"{task['task_date']} {task['task_time']}", "%Y-%m-%d %H:%M"
                    )
                    remind_at = task_dt - timedelta(minutes=task["reminder_minutes"])
                    if remind_at > datetime.now():
                        self.schedule_reminder(
                            application, uid, task["id"],
                            task["title"], remind_at, task["task_time"]
                        )
                        total_restored += 1
                except Exception as e:
                    logger.error(f"Failed to restore reminder {task['id']}: {e}")
        
        logger.info(f"Restored {total_restored} reminders from database")

    def shutdown(self):
        self.scheduler.shutdown(wait=False)
