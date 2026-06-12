
import requests
import re
import os
import logging
import time
import random
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def google_search(query, num=5):
    try:
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for g in soup.select("div.g"):
            link = g.select_one("a")
            snippet = g.select_one(".VwiC3b")
            if link:
                results.append({
                    "url": link.get("href", ""),
                    "snippet": snippet.get_text() if snippet else ""
                })
        return results
    except Exception as e:
        logger.error(f"Google search failed: {e}")
        return []

def find_company_website(company_name):
    results = google_search(f"{company_name} startup official website", num=5)
    blocked = ["linkedin", "twitter", "facebook", "crunchbase", "tracxn",
               "wikipedia", "youtube", "instagram", "google", "bloomberg"]
    for r in results:
        url = r["url"]
        if url.startswith("http") and not any(b in url for b in blocked):
            domain_match = re.search(r"https?://(?:www\.)?([a-z0-9\-]+\.[a-z]{2,})", url)
            if domain_match:
                return domain_match.group(1), url
    return "", ""

def scrape_website_for_emails(url):
    emails = set()
    pages_to_try = [url, url.rstrip("/") + "/about", url.rstrip("/") + "/team",
                    url.rstrip("/") + "/contact", url.rstrip("/") + "/founders"]
    for page in pages_to_try:
        try:
            resp = requests.get(page, headers=HEADERS, timeout=8)
            found = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", resp.text)
            for email in found:
                if not any(x in email.lower() for x in ["noreply", "no-reply", "support",
                                                          "info@", "hello@", "contact@",
                                                          "example", "test@"]):
                    emails.add(email.lower())
            time.sleep(random.uniform(0.5, 1.5))
        except:
            continue
    return list(emails)

def find_linkedin_url(name, company):
    results = google_search(f'site:linkedin.com/in "{name}" "{company}"', num=3)
    for r in results:
        url = r["url"]
        if "linkedin.com/in/" in url:
            match = re.search(r"(https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-]+)", url)
            if match:
                return match.group(1)
    results = google_search(f'site:linkedin.com/in {name} {company} founder', num=3)
    for r in results:
        url = r["url"]
        if "linkedin.com/in/" in url:
            match = re.search(r"(https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-]+)", url)
            if match:
                return match.group(1)
    return ""

def generate_email_from_pattern(first_name, last_name, domain):
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    return f"{first}@{domain}", [
        f"{first}@{domain}",
        f"{first}.{last}@{domain}",
        f"{first[0]}{last}@{domain}",
        f"{first}{last}@{domain}",
    ]

def fetch_startups_with_contacts(excel_path=None, max_startups=10):
    import pandas as pd
    
    if not excel_path or not os.path.exists(excel_path):
        logger.error(f"No Excel file found at {excel_path}")
        return []
    
    df = pd.read_excel(excel_path)
    name_col = next((c for c in df.columns if "name" in c.lower() and "company" not in c.lower()), None)
    company_col = next((c for c in df.columns if "company" in c.lower()), None)
    role_col = next((c for c in df.columns if "role" in c.lower() or "title" in c.lower()), None)
    summary_col = next((c for c in df.columns if "summary" in c.lower() or "background" in c.lower()), None)
    
    if not name_col or not company_col:
        logger.error("Could not find Name/Company columns")
        return []
    
    results = []
    processed = 0
    
    for _, row in df.iterrows():
        if processed >= max_startups:
            break
        name = str(row.get(name_col, "")).strip()
        company = str(row.get(company_col, "")).strip()
        role = str(row.get(role_col, "")).strip() if role_col else ""
        summary = str(row.get(summary_col, "")).strip() if summary_col else ""
        
        if not name or not company or name == "nan":
            continue
        
        first_name = name.split()[0]
        last_name = name.split()[-1] if len(name.split()) > 1 else ""
        
        logger.info(f"Processing {name} at {company}...")
        
        domain, website_url = find_company_website(company)
        time.sleep(random.uniform(1, 2))
        
        emails_found = []
        if website_url:
            emails_found = scrape_website_for_emails(website_url)
        
        linkedin_url = find_linkedin_url(name, company)
        time.sleep(random.uniform(1, 2))
        
        if emails_found:
            email = emails_found[0]
            outreach_type = "email"
        elif domain:
            email, _ = generate_email_from_pattern(first_name, last_name, domain)
            outreach_type = "email_generated"
        else:
            email = ""
            outreach_type = "linkedin"
        
        contact = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "title": role,
            "linkedin_url": linkedin_url,
            "outreach_type": outreach_type,
            "source": "excel_upload"
        }
        
        results.append({
            "name": company,
            "website": domain,
            "description": f"{summary} | Role: {role}",
            "sector": "AI/Tech",
            "funding_amount_usd": 500000,
            "funding_round": "seed",
            "funding_date": "2024",
            "location": "",
            "source": "excel_upload",
            "contacts": [contact]
        })
        processed += 1
    
    logger.info(f"Processed {len(results)} founders")
    return results
