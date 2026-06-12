
import time
import random
import logging
import os
from playwright.sync_api import sync_playwright
from groq import Groq

logger = logging.getLogger(__name__)

def generate_linkedin_message(contact, company):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    prompt = f"""Write a 250-300 character LinkedIn connection request message from Tanay Jain to {contact.get("first_name")} at {company.get("name")}.

About Tanay: Final year student, joining BCG in September 2026, looking for a 2-month remote internship before joining.
About the founder: {company.get("description", "")}

Rules:
- Must be under 300 characters
- Mention their specific company
- Ask for 2-month remote internship
- Sound genuine
- No hashtags

Write the message only:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()[:300]

def send_linkedin_connection(linkedin_url, message):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://www.linkedin.com/login")
            page.fill("#username", os.environ.get("LINKEDIN_EMAIL", ""))
            page.fill("#password", os.environ.get("LINKEDIN_PASSWORD", ""))
            page.click("button[type=submit]")
            page.wait_for_timeout(3000)
            
            page.goto(linkedin_url)
            page.wait_for_timeout(2000)
            
            connect_btn = page.query_selector("button:has-text(\'Connect\')")
            if connect_btn:
                connect_btn.click()
                page.wait_for_timeout(1000)
                add_note = page.query_selector("button:has-text(\'Add a note\')")
                if add_note:
                    add_note.click()
                    page.wait_for_timeout(500)
                    page.fill("textarea[name=message]", message)
                    page.click("button:has-text(\'Send\')")
                    page.wait_for_timeout(1000)
                    logger.info(f"Connection sent to {linkedin_url}")
                    browser.close()
                    return True
            browser.close()
            return False
        except Exception as e:
            logger.error(f"LinkedIn failed: {e}")
            browser.close()
            return False
