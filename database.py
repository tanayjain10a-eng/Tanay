from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Startup(db.Model):
    __tablename__ = "startups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    website = db.Column(db.String(300))
    linkedin_url = db.Column(db.String(300))
    sector = db.Column(db.String(100))
    funding_amount_usd = db.Column(db.Float)
    funding_round = db.Column(db.String(50))
    funding_date = db.Column(db.String(50))
    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    source = db.Column(db.String(50))   # apollo / tracxn / manual
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    contacts = db.relationship("Contact", backref="startup", lazy=True)


class Contact(db.Model):
    __tablename__ = "contacts"
    id = db.Column(db.Integer, primary_key=True)
    startup_id = db.Column(db.Integer, db.ForeignKey("startups.id"), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(200), unique=True)
    title = db.Column(db.String(200))
    linkedin_url = db.Column(db.String(300))
    source = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    emails = db.relationship("Email", backref="contact", lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()


class Email(db.Model):
    __tablename__ = "emails"
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=False)
    subject = db.Column(db.String(300))
    body = db.Column(db.Text)
    status = db.Column(db.String(30), default="pending")  # pending / approved / rejected / sent / failed
    scheduled_date = db.Column(db.Date)
    sent_at = db.Column(db.DateTime)
    gmail_message_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_subject = db.Column(db.String(300))
    edited_body = db.Column(db.Text)

    @property
    def final_subject(self):
        return self.edited_subject or self.subject

    @property
    def final_body(self):
        return self.edited_body or self.body
