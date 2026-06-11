# Cold Mail App — Setup Guide

## 1. Install dependencies
```bash
pip install -r requirements.txt
```

## 2. Set up API keys
```bash
cp .env.example .env
# Edit .env and fill in your keys
```

### Apollo.io (primary data source)
1. Sign up free at https://app.apollo.io
2. Go to Settings → Integrations → API
3. Copy your API key into `.env`

### Anthropic (email generation)
1. Get a key at https://console.anthropic.com/keys
2. Add to `.env`

### Tracxn (optional)
- Sign up at tracxn.com and request API access.

## 3. Set up Gmail OAuth
1. Go to https://console.cloud.google.com
2. Create a project → Enable **Gmail API**
3. Create credentials: OAuth 2.0 Client ID → Desktop App
4. Download JSON → save as `credentials.json` in this folder
5. Run the auth flow once:
```bash
python gmail_client.py --auth
```
This opens a browser, log in with **tanayjain10a@gmail.com**, and grants send permission. Saves `token.json`.

## 4. Run the app
```bash
python app.py
```
Open http://localhost:5050

## 5. Daily workflow
1. Click **Scrape & Draft** — fetches startups from Apollo, finds 5-7 contacts each, generates personalised emails via Claude.
2. Go to **Review Emails** — read, edit, approve or reject.
3. Approved emails auto-send at **9:00 AM IST Mon–Fri** (up to 35/day).
4. You can also use **Send Now** on any individual email.

## Notes
- LinkedIn data is accessed via Apollo, which aggregates it legally (no direct scraping).
- Gmail API send limit: ~500 emails/day on a personal account — well within our 35/day target.
- `cold_mail.db` (SQLite) stores all data locally.
