"""Optional reminder worker. Run separately from Streamlit.

This starter scans for approved reviews due in the next 24 hours and sends one
reminder per review by checking the email log. Test with your own email first.
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine, text
from google_services import send_email

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./internship.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {},
    pool_pre_ping=True,
)

def reminder_scan():
    now = datetime.now()
    cutoff = now + timedelta(hours=24)
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT r.id AS review_id, r.next_review_at, t.title,
                   s.name, s.email, r.review_number
            FROM reviews r
            JOIN tasks t ON t.id = r.task_id
            JOIN students s ON s.id = t.student_id
            WHERE r.approved = TRUE
              AND r.next_review_at >= :now
              AND r.next_review_at <= :cutoff
        """), {"now": now, "cutoff": cutoff}).mappings().all()
        for row in rows:
            subject = f"Reminder: upcoming internship review #{row['review_number'] + 1} — {row['title']}"
            already_sent = conn.execute(text("""
                SELECT 1 FROM email_logs
                WHERE recipient = :recipient AND subject = :subject AND status = 'sent'
                LIMIT 1
            """), {"recipient": row['email'], "subject": subject}).first()
            if already_sent:
                continue
            body = (f"Hello {row['name']},\n\nThis is a reminder that your next internship review "
                    f"is scheduled for {row['next_review_at']}.\nTask: {row['title']}\n\n"
                    "Please prepare your updated work. Open the calendar invitation for the meeting link.\n")
            try:
                provider_id = send_email(row['email'], subject, body)
                conn.execute(text("""
                    INSERT INTO email_logs (recipient, subject, status, provider_id, created_at)
                    VALUES (:recipient, :subject, 'sent', :provider_id, :created_at)
                """), {"recipient": row['email'], "subject": subject,
                      "provider_id": provider_id, "created_at": datetime.utcnow()})
                print(f"Reminder sent to {row['email']} for review {row['review_id']}")
            except Exception as exc:
                conn.execute(text("""
                    INSERT INTO email_logs (recipient, subject, status, provider_id, created_at)
                    VALUES (:recipient, :subject, 'failed', NULL, :created_at)
                """), {"recipient": row['email'], "subject": subject,
                      "created_at": datetime.utcnow()})
                print(f"Reminder failed for review {row['review_id']}: {exc}")

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(reminder_scan, "interval", minutes=15, id="review_reminders",
                      max_instances=1, coalesce=True)
    reminder_scan()
    scheduler.start()
