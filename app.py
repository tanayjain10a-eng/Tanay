"""
Cold Mailing Application — Flask web server.
Run: python app.py
"""
import logging
from datetime import date, timedelta

from flask import Flask, render_template, redirect, url_for, request, jsonify, flash

from config import DATABASE_URL, DAILY_EMAIL_LIMIT
from database import db, Startup, Contact, Email
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "tanay-cold-mail-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

scheduler = start_scheduler(app)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    total_startups = Startup.query.count()
    total_contacts = Contact.query.count()
    pending = Email.query.filter_by(status="pending").count()
    approved = Email.query.filter_by(status="approved").count()
    sent = Email.query.filter_by(status="sent").count()
    failed = Email.query.filter_by(status="failed").count()
    rejected = Email.query.filter_by(status="rejected").count()
    return render_template("dashboard.html", **locals())


# ---------------------------------------------------------------------------
# Scrape + Generate
# ---------------------------------------------------------------------------

@app.route("/scrape", methods=["POST"])
def scrape():
    """Fetch startups + contacts from Apollo/Tracxn and generate draft emails."""
    from scraper import fetch_startups_with_contacts
    from email_generator import bulk_generate

    max_startups = int(request.form.get("max_startups", 10))
    results = fetch_startups_with_contacts(max_startups=max_startups)

    added_startups = 0
    added_contacts = 0
    generated_emails = 0
    scheduled_date = _next_weekday()

    for startup_data in results:
        # Upsert startup
        existing = Startup.query.filter_by(name=startup_data["name"]).first()
        if existing:
            startup = existing
        else:
            startup = Startup(
                name=startup_data["name"],
                website=startup_data.get("website", ""),
                linkedin_url=startup_data.get("linkedin_url", ""),
                sector=startup_data.get("sector", ""),
                funding_amount_usd=startup_data.get("funding_amount_usd", 0),
                funding_round=startup_data.get("funding_round", "seed"),
                funding_date=startup_data.get("funding_date", ""),
                description=startup_data.get("description", ""),
                location=startup_data.get("location", ""),
                source=startup_data.get("source", ""),
            )
            db.session.add(startup)
            db.session.flush()
            added_startups += 1

        contacts_payload = []
        for c in startup_data.get("contacts", []):
            if not c.get("email"):
                continue
            existing_c = Contact.query.filter_by(email=c["email"]).first()
            if existing_c:
                contact = existing_c
            else:
                contact = Contact(
                    startup_id=startup.id,
                    first_name=c.get("first_name", ""),
                    last_name=c.get("last_name", ""),
                    email=c["email"],
                    title=c.get("title", ""),
                    linkedin_url=c.get("linkedin_url", ""),
                    source=c.get("source", "apollo"),
                )
                db.session.add(contact)
                db.session.flush()
                added_contacts += 1

            # Only generate if no email exists yet for this contact
            if not Email.query.filter_by(contact_id=contact.id).first():
                contacts_payload.append({
                    "contact_id": contact.id,
                    "first_name": contact.first_name,
                    "title": contact.title,
                    "startup_name": startup.name,
                    "startup_description": startup.description,
                    "startup_sector": startup.sector,
                    "startup_funding": startup.funding_amount_usd or 0,
                })

        # Generate emails in bulk for this startup's contacts
        if contacts_payload:
            email_results = bulk_generate(contacts_payload)
            for er in email_results:
                if er.get("error") or not er.get("subject"):
                    continue
                email_obj = Email(
                    contact_id=er["contact_id"],
                    subject=er["subject"],
                    body=er["body"],
                    status="pending",
                    scheduled_date=scheduled_date,
                )
                db.session.add(email_obj)
                generated_emails += 1

    db.session.commit()
    flash(f"Scraped {added_startups} new startups, {added_contacts} contacts, generated {generated_emails} draft emails.", "success")
    return redirect(url_for("review"))


# ---------------------------------------------------------------------------
# Review & Approval
# ---------------------------------------------------------------------------

@app.route("/review")
def review():
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "pending")
    query = (
        Email.query
        .join(Contact, Email.contact_id == Contact.id)
        .join(Startup, Contact.startup_id == Startup.id)
        .filter(Email.status == status_filter)
        .order_by(Startup.name, Email.id)
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template("review.html", emails=query, status_filter=status_filter)


@app.route("/email/<int:email_id>", methods=["GET"])
def view_email(email_id):
    email_obj = Email.query.get_or_404(email_id)
    contact = Contact.query.get(email_obj.contact_id)
    startup = Startup.query.get(contact.startup_id)
    return render_template("email_detail.html", email=email_obj, contact=contact, startup=startup)


@app.route("/email/<int:email_id>/approve", methods=["POST"])
def approve_email(email_id):
    email_obj = Email.query.get_or_404(email_id)
    edited_subject = request.form.get("subject", "").strip()
    edited_body = request.form.get("body", "").strip()
    if edited_subject:
        email_obj.edited_subject = edited_subject
    if edited_body:
        email_obj.edited_body = edited_body
    email_obj.status = "approved"
    db.session.commit()
    flash("Email approved.", "success")
    return redirect(request.referrer or url_for("review"))


@app.route("/email/<int:email_id>/reject", methods=["POST"])
def reject_email(email_id):
    email_obj = Email.query.get_or_404(email_id)
    email_obj.status = "rejected"
    db.session.commit()
    flash("Email rejected.", "info")
    return redirect(request.referrer or url_for("review"))


@app.route("/approve-all", methods=["POST"])
def approve_all():
    """Bulk-approve all pending emails."""
    count = Email.query.filter_by(status="pending").update({"status": "approved"})
    db.session.commit()
    flash(f"Approved {count} emails.", "success")
    return redirect(url_for("review"))


@app.route("/reject-all", methods=["POST"])
def reject_all():
    """Bulk-reject all pending emails."""
    count = Email.query.filter_by(status="pending").update({"status": "rejected"})
    db.session.commit()
    flash(f"Rejected {count} emails.", "info")
    return redirect(url_for("review"))


# ---------------------------------------------------------------------------
# Manual single send (testing)
# ---------------------------------------------------------------------------

@app.route("/email/<int:email_id>/send-now", methods=["POST"])
def send_now(email_id):
    from gmail_client import send_email as gmail_send
    from datetime import datetime
    email_obj = Email.query.get_or_404(email_id)
    if email_obj.status not in ("approved", "pending"):
        flash("Email must be approved or pending to send.", "danger")
        return redirect(request.referrer or url_for("review"))
    contact = Contact.query.get(email_obj.contact_id)
    msg_id = gmail_send(contact.email, email_obj.final_subject, email_obj.final_body)
    if msg_id:
        email_obj.status = "sent"
        email_obj.sent_at = datetime.utcnow()
        email_obj.gmail_message_id = msg_id
        db.session.commit()
        flash(f"Sent to {contact.email}.", "success")
    else:
        flash("Send failed — check logs.", "danger")
    return redirect(request.referrer or url_for("review"))


# ---------------------------------------------------------------------------
# Startups & Contacts views
# ---------------------------------------------------------------------------

@app.route("/startups")
def startups():
    all_startups = Startup.query.order_by(Startup.funding_amount_usd.desc()).all()
    return render_template("startups.html", startups=all_startups)


@app.route("/startup/<int:startup_id>")
def startup_detail(startup_id):
    startup = Startup.query.get_or_404(startup_id)
    contacts = Contact.query.filter_by(startup_id=startup_id).all()
    return render_template("startup_detail.html", startup=startup, contacts=contacts)


# ---------------------------------------------------------------------------
# API — JSON endpoints for status polling
# ---------------------------------------------------------------------------

@app.route("/api/stats")
def api_stats():
    return jsonify({
        "startups": Startup.query.count(),
        "contacts": Contact.query.count(),
        "pending": Email.query.filter_by(status="pending").count(),
        "approved": Email.query.filter_by(status="approved").count(),
        "sent": Email.query.filter_by(status="sent").count(),
        "failed": Email.query.filter_by(status="failed").count(),
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_weekday(from_date: date | None = None) -> date:
    d = from_date or date.today()
    if d.weekday() >= 5:
        d += timedelta(days=7 - d.weekday())
    return d


if __name__ == "__main__":
    app.run(debug=True, port=5050, use_reloader=False)
