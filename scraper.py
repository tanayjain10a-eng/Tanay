"""
Data collection from Apollo.io and Tracxn APIs.
Apollo is the primary source — it aggregates LinkedIn data legally.
Tracxn is used to cross-reference seed-round startups.
"""
import requests
import logging
from datetime import datetime, timedelta
from config import (
    APOLLO_API_KEY, TRACXN_API_KEY,
    MIN_FUNDING_USD, MAX_FUNDING_AGE_DAYS,
    TARGET_SECTORS, TARGET_ROUND, EMPLOYEES_PER_STARTUP
)

logger = logging.getLogger(__name__)

APOLLO_BASE = "https://api.apollo.io/v1"
TRACXN_BASE = "https://tracxn.com/api/2.1"


# ---------------------------------------------------------------------------
# Apollo helpers
# ---------------------------------------------------------------------------

def apollo_headers():
    return {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": APOLLO_API_KEY}


def search_startups_apollo(page: int = 1, per_page: int = 25) -> list[dict]:
    """Search Apollo for AI/Tech companies that raised a seed round recently."""
    cutoff = (datetime.utcnow() - timedelta(days=MAX_FUNDING_AGE_DAYS)).strftime("%Y-%m-%d")
    payload = {
        "page": page,
        "per_page": per_page,
        "organization_num_employees_ranges": ["1,200"],
        "organization_latest_funding_stage_cd": ["seed"],
        "organization_keywords": TARGET_SECTORS[:4],
        "currently_using_any_of_technology_uids": [],
        "q_organization_keyword_tags": ["artificial intelligence", "machine learning", "saas"],
        "sort_by_field": "funding_total",
        "sort_ascending": False,
    }
    try:
        resp = requests.post(f"{APOLLO_BASE}/mixed_companies/search", json=payload, headers=apollo_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        orgs = data.get("organizations", [])
        # Filter by funding amount and recency
        filtered = []
        for org in orgs:
            funding = org.get("latest_funding_round_amount") or 0
            funding_date_str = org.get("latest_funding_round_date") or ""
            if funding >= MIN_FUNDING_USD and funding_date_str >= cutoff:
                filtered.append(org)
        return filtered
    except Exception as e:
        logger.error(f"Apollo company search failed: {e}")
        return []


def enrich_company_apollo(domain: str) -> dict:
    """Get detailed company info from Apollo by domain."""
    try:
        resp = requests.get(
            f"{APOLLO_BASE}/organizations/enrich",
            params={"domain": domain},
            headers=apollo_headers(),
            timeout=15
        )
        resp.raise_for_status()
        return resp.json().get("organization", {})
    except Exception as e:
        logger.error(f"Apollo company enrich failed for {domain}: {e}")
        return {}


def search_contacts_apollo(org_id: str, company_name: str, limit: int = EMPLOYEES_PER_STARTUP) -> list[dict]:
    """Find key contacts at a startup — founders, C-suite, VPs, engineering leads."""
    titles = [
        "founder", "co-founder", "ceo", "cto", "coo", "vp engineering",
        "head of product", "chief of staff", "director", "head of growth",
        "engineering manager", "vp product"
    ]
    payload = {
        "page": 1,
        "per_page": limit * 2,
        "organization_ids": [org_id],
        "person_titles": titles,
        "contact_email_status": ["verified", "likely to engage"],
    }
    try:
        resp = requests.post(f"{APOLLO_BASE}/mixed_people/search", json=payload, headers=apollo_headers(), timeout=15)
        resp.raise_for_status()
        people = resp.json().get("people", [])
        # Prefer people with verified emails
        people_with_email = [p for p in people if p.get("email")]
        return people_with_email[:limit]
    except Exception as e:
        logger.error(f"Apollo contact search failed for {company_name}: {e}")
        return []


def reveal_email_apollo(person_id: str) -> str | None:
    """Reveal (unlock) a contact's email using Apollo's reveal endpoint."""
    try:
        resp = requests.post(
            f"{APOLLO_BASE}/people/match",
            json={"id": person_id, "reveal_personal_emails": False},
            headers=apollo_headers(),
            timeout=15
        )
        resp.raise_for_status()
        person = resp.json().get("person", {})
        return person.get("email")
    except Exception as e:
        logger.error(f"Apollo email reveal failed for {person_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Tracxn helpers
# ---------------------------------------------------------------------------

def search_startups_tracxn(page: int = 1) -> list[dict]:
    """Search Tracxn for recent AI seed-stage startups."""
    if not TRACXN_API_KEY:
        return []
    try:
        cutoff_year = datetime.utcnow().year - 1
        resp = requests.post(
            f"{TRACXN_BASE}/companies/search",
            json={
                "accessToken": TRACXN_API_KEY,
                "filters": {
                    "fundingRounds": [{"roundType": "Seed", "minAmount": MIN_FUNDING_USD}],
                    "sectors": ["Artificial Intelligence", "Machine Learning", "SaaS", "Fintech"],
                    "fundingDateFrom": f"{cutoff_year}-01-01",
                },
                "pageNumber": page,
                "pageSize": 20,
                "sortBy": "latestFundingDate",
                "sortOrder": "desc",
            },
            timeout=15
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("companies", [])
    except Exception as e:
        logger.error(f"Tracxn search failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def fetch_startups_with_contacts(max_startups: int = 10) -> list[dict]:
    """
    Pull startups + contacts from Apollo (primary) and Tracxn (supplement).
    Returns a list of dicts ready to be persisted.
    """
    results = []
    seen_names = set()

    # Apollo — multiple pages
    for page in range(1, 5):
        if len(results) >= max_startups:
            break
        orgs = search_startups_apollo(page=page)
        for org in orgs:
            if len(results) >= max_startups:
                break
            name = org.get("name", "").strip()
            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            org_id = org.get("id", "")
            contacts_raw = search_contacts_apollo(org_id, name) if org_id else []
            contacts = []
            for p in contacts_raw:
                email = p.get("email") or reveal_email_apollo(p.get("id", ""))
                if not email:
                    continue
                contacts.append({
                    "first_name": p.get("first_name", ""),
                    "last_name": p.get("last_name", ""),
                    "email": email,
                    "title": p.get("title", ""),
                    "linkedin_url": p.get("linkedin_url", ""),
                    "source": "apollo",
                })

            results.append({
                "name": name,
                "website": org.get("website_url", ""),
                "linkedin_url": org.get("linkedin_url", ""),
                "sector": ", ".join(org.get("keywords", [])[:3]),
                "funding_amount_usd": org.get("latest_funding_round_amount", 0),
                "funding_round": org.get("latest_funding_stage", "seed"),
                "funding_date": org.get("latest_funding_round_date", ""),
                "description": org.get("short_description", ""),
                "location": (org.get("primary_domain") or ""),
                "source": "apollo",
                "contacts": contacts,
            })

    # Tracxn supplement
    if len(results) < max_startups:
        tracxn_orgs = search_startups_tracxn()
        for org in tracxn_orgs:
            if len(results) >= max_startups:
                break
            name = org.get("name", "").strip()
            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            results.append({
                "name": name,
                "website": org.get("website", ""),
                "linkedin_url": org.get("linkedinUrl", ""),
                "sector": org.get("sector", ""),
                "funding_amount_usd": org.get("latestRoundAmount", 0),
                "funding_round": "seed",
                "funding_date": org.get("latestFundingDate", ""),
                "description": org.get("description", ""),
                "location": org.get("hq", ""),
                "source": "tracxn",
                "contacts": [],  # Tracxn contacts fetched via Apollo by domain
            })

    logger.info(f"Fetched {len(results)} startups with contacts")
    return results
