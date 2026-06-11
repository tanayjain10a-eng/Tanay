"""
Generates personalised cold emails using Claude (Anthropic API).
Each email is tailored to the contact's role and startup's product/mission.
"""
import anthropic
import logging
from config import ANTHROPIC_API_KEY, SENDER_NAME, SENDER_EMAIL

logger = logging.getLogger(__name__)

RESUME_SUMMARY = """
Tanay Jain — 20-year-old B.Com (Hons.) student at Shri Ram College of Commerce (CGPA 9.14).
Incoming Associate at BCG. Former intern at Deutsche Bank IB (valued €180mn+ in real-estate credit deals),
Conditor Capital PE (screened 350+ M&A targets), Venture Catalysts VC (sourced 20+ startups, assisted on 3 live deals worth ₹5Cr+),
and Deloitte Valuations. Founded Onaya Foundation (upcycled 10,000m+ waste fabric, 8,000+ dresses to underprivileged children).
National winner at 40+ consulting and strategy competitions. Global semi-finalist at Enactus World Cup '24.
Highly analytical, commercially aware, and execution-driven. Seeking a 2-month remote internship in an AI/tech startup.
"""


def generate_email(
    contact_first_name: str,
    contact_title: str,
    startup_name: str,
    startup_description: str,
    startup_sector: str,
    startup_funding: float,
) -> tuple[str, str]:
    """
    Returns (subject, body) for a personalised cold email.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are helping Tanay Jain write a cold outreach email for a 2-month remote internship at a startup.

Recipient details:
- First name: {contact_first_name}
- Title: {contact_title}
- Company: {startup_name}
- Company description: {startup_description}
- Sector: {startup_sector}
- Recent funding: ~${startup_funding:,.0f} seed round

Tanay's background:
{RESUME_SUMMARY}

Write a cold email from Tanay to this person. Rules:
1. Subject line: crisp, specific, no more than 10 words. No generic "internship application" phrases.
2. Opening line: reference something SPECIFIC about the company (product, mission, recent funding news, or sector problem they solve). No flattery.
3. Paragraph 2: draw ONE tight connection between Tanay's most relevant experience and what this company actually needs. Be concrete — mention deal sizes, metrics, or specific skills.
4. Paragraph 3: clear ask — 2-month remote internship. One sentence about what Tanay can contribute.
5. Closing: light, confident. No "I look forward to hearing from you" clichés.
6. Total length: 150–200 words MAX.
7. Tone: peer-level, not sycophantic. Tanay is highly accomplished — let that show without bragging.
8. Do NOT include a signature block — just the email body ending after the close.
9. Output format: first line = subject, then a blank line, then the body. Nothing else.

Sender email for reference: {SENDER_EMAIL}
Sender name: {SENDER_NAME}
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    lines = raw.split("\n", 2)
    subject = lines[0].strip()
    # Remove "Subject:" prefix if model adds it
    if subject.lower().startswith("subject:"):
        subject = subject[8:].strip()
    body = lines[2].strip() if len(lines) >= 3 else (lines[1].strip() if len(lines) >= 2 else "")

    # Append signature
    body += f"\n\nBest,\n{SENDER_NAME}\n{SENDER_EMAIL}\nLinkedIn: https://www.linkedin.com/in/tanayjain10a"

    return subject, body


def bulk_generate(contacts_data: list[dict]) -> list[dict]:
    """
    contacts_data: list of dicts with keys:
        contact_id, first_name, title, startup_name,
        startup_description, startup_sector, startup_funding
    Returns list with added 'subject' and 'body' keys.
    """
    results = []
    for item in contacts_data:
        try:
            subject, body = generate_email(
                contact_first_name=item.get("first_name", "there"),
                contact_title=item.get("title", ""),
                startup_name=item.get("startup_name", ""),
                startup_description=item.get("startup_description", ""),
                startup_sector=item.get("startup_sector", ""),
                startup_funding=item.get("startup_funding", 0),
            )
            results.append({**item, "subject": subject, "body": body, "error": None})
        except Exception as e:
            logger.error(f"Email generation failed for contact {item.get('contact_id')}: {e}")
            results.append({**item, "subject": "", "body": "", "error": str(e)})
    return results
