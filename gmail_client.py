"""
Gmail API client for sending emails via tanayjain10a@gmail.com.
"""
import base64
import logging
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, SENDER_EMAIL, SENDER_NAME

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

RESUME_PATHS = [
    "/content/Tanay/resume.pdf",
    "/drive/MyDrive/ColdMailer/resume.pdf",
]

def get_gmail_service():
    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GMAIL_CREDENTIALS_FILE):
                raise FileNotFoundError(f"Gmail credentials file not found: {GMAIL_CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GMAIL_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def send_email(to_email: str, subject: str, body: str) -> str | None:
    try:
        service = get_gmail_service()

        # Find resume
        resume_path = None
        for path in RESUME_PATHS:
            if os.path.exists(path):
                resume_path = path
                break

        if resume_path:
            message = MIMEMultipart()
            message.attach(MIMEText(body, "plain"))
            with open(resume_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename="Tanay_Jain_Resume.pdf")
            message.attach(part)
            logger.info(f"Resume attached from {resume_path}")
        else:
            message = MIMEText(body, "plain")
            logger.warning("Resume not found — sending without attachment")

        message["to"] = to_email
        message["from"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        message["subject"] = subject

        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me", body={"raw": encoded}
        ).execute()
        logger.info(f"Email sent to {to_email} — Gmail ID: {result['id']}")
        return result["id"]
    except HttpError as e:
        logger.error(f"Gmail API error sending to {to_email}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending to {to_email}: {e}")
        return None


if __name__ == "__main__":
    if "--auth" in sys.argv:
        service = get_gmail_service()
        print("Gmail authenticated successfully.")
