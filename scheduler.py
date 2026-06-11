"""
APScheduler job: every weekday at 9 AM IST, send up to DAILY_EMAIL_LIMIT approved emails.
"""
import logging
from datetime import date, datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler

from config import DAILY_EMAIL_LIMIT, SEND_HOUR_IST
from database import db, Email, Contact, Startup
from gmail_client import send_email

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


def send_approved_emails(app):
    with app.app_context():
        today = date.today()
        # Skip weekends (0=Mon … 6=Sun)
        if today.weekday() >= 5:
            logger.info("Weekend — skipping email send.")
            return

        approved = (
            Email.query
            .filter_by(status="approved")
            .filter(Email.scheduled_date <= today)
            .limit(DAILY_EMAIL_LIMIT)
            .all()
        )
        logger.info(f"Sending {len(approved)} approved emails for {today}")
        for email_obj in approved:
            contact = Contact.query.get(email_obj.contact_id)
            if not contact:
                continue
            msg_id = send_email(contact.email, email_obj.final_subject, email_obj.final_body)
            if msg_id:
                email_obj.status = "sent"
                email_obj.sent_at = datetime.utcnow()
                email_obj.gmail_message_id = msg_id
            else:
                email_obj.status = "failed"
            db.session.commit()


def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone=IST)
    scheduler.add_job(
        func=lambda: send_approved_emails(app),
        trigger="cron",
        day_of_week="mon-fri",
        hour=SEND_HOUR_IST,
        minute=0,
        id="daily_send",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — emails send at {SEND_HOUR_IST}:00 IST on weekdays.")
    return scheduler
