import os
from dotenv import load_dotenv

load_dotenv()

# Gmail sender
SENDER_EMAIL = "tanayjain10a@gmail.com"
SENDER_NAME = "Tanay Jain"

# API Keys — set in .env
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TRACXN_API_KEY = os.getenv("TRACXN_API_KEY", "")

# Gmail OAuth
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = "token.json"

# Targeting criteria
MIN_FUNDING_USD = 500_000
MAX_FUNDING_AGE_DAYS = 365
TARGET_SECTORS = ["artificial intelligence", "machine learning", "deep tech", "saas", "fintech", "edtech", "healthtech", "b2b software"]
TARGET_ROUND = "seed"
EMPLOYEES_PER_STARTUP = 6   # aim for 5-7
DAILY_EMAIL_LIMIT = 35       # sends 35 per day; tune between 30-40
SEND_HOUR_IST = 9            # 9 AM IST

# SQLite DB
DATABASE_URL = "sqlite:///cold_mail.db"
