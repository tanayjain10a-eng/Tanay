
import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

TANAY_BACKGROUND = """
Name: Tanay Jain
Email: tanayjain10a@gmail.com
Seeking: 2-month remote internship in AI/ML/SaaS startups
Background:
- Final year student passionate about AI and product development
- Experience with Python, data analysis, and business operations
- Joining BCG (Boston Consulting Group) as a full-time consultant in September 2026
- Looking to gain startup experience before starting at BCG
- Available for remote work immediately
"""

def generate_email(contact, company):
    description = company.get("description", "")
    
    prompt = f"""Write a 150-200 word cold email from Tanay Jain to {contact.get("first_name", "")} {contact.get("last_name", "")} at {company.get("name", "")}.

About Tanay:
{TANAY_BACKGROUND}

About the founder and company:
{description}

Rules:
- DO NOT use any placeholder text like [relevant field] or [X years]
- Reference the founder's specific background from the description (e.g. their previous companies, university)
- Mention Tanay is joining BCG in September to establish credibility
- Keep it under 200 words
- End with a clear ask for a 2-month remote internship
- Sign off: Tanay Jain | tanayjain10a@gmail.com

Write the complete email now:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def bulk_generate(contacts_payload):
    results = []
    for item in contacts_payload:
        contact = {
            "first_name": item.get("first_name", ""),
            "last_name": item.get("last_name", ""),
            "title": item.get("title", ""),
        }
        company = {
            "name": item.get("startup_name", ""),
            "description": item.get("startup_description", ""),
        }
        body = generate_email(contact, company)
        results.append({
            "contact_id": item["contact_id"],
            "subject": f"Internship Inquiry - Tanay Jain",
            "body": body
        })
    return results
