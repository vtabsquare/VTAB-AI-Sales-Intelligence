import html
import os
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlsplit, urlunsplit

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import AgentRun, Company, Opportunity
from app.models.platform import DiscoverySource, ServicePortfolio
from app.services.public_http import public_get

DEFAULT_SERVICES = [
    ("Microsoft Data & BI", "Power BI, Microsoft Fabric, reporting and analytics", ["power bi", "microsoft fabric", "business intelligence", "reporting", "analytics"]),
    ("Data Engineering & Modernization", "Databricks, lakehouse, ETL and data platform modernization", ["databricks", "lakehouse", "data engineering", "etl", "data platform", "sql server migration"]),
    ("AI Applications & Automation", "AI applications, agents and workflow automation", ["artificial intelligence", "generative ai", "ai agent", "automation", "workflow automation"]),
    ("Business Applications", "Dynamics 365, Power Platform and custom applications", ["dynamics 365", "power platform", "power automate", "application development", "software development"]),
    ("IT Service & Support", "Managed IT support, application maintenance and service desk", ["managed it", "it support", "service desk", "application maintenance"]),
    ("Cloud & Infrastructure", "Cloud migration and infrastructure modernization", ["cloud migration", "azure migration", "infrastructure modernization", "managed cloud"]),
]

# Official/public procurement destinations. WEB_SEARCH means the search query is constrained to the host.
PUBLIC_SOURCES = [
    ("EU TED", "https://ted.europa.eu", ["European Union", "Europe"]),
    ("Ireland eTenders", "https://www.etenders.gov.ie", ["Ireland"]),
    ("UK Find a Tender", "https://www.find-tender.service.gov.uk", ["United Kingdom"]),
    ("UK Contracts Finder", "https://www.contractsfinder.service.gov.uk", ["United Kingdom"]),
    ("Australia AusTender", "https://www.tenders.gov.au", ["Australia"]),
    ("Singapore GeBIZ", "https://www.gebiz.gov.sg", ["Singapore"]),
    ("US SAM.gov", "https://sam.gov", ["United States"]),
    ("New Zealand GETS", "https://www.gets.govt.nz", ["New Zealand"]),
    ("CanadaBuys", "https://canadabuys.canada.ca", ["Canada"]),
]


def seed_defaults(db: Session):
    if db.query(ServicePortfolio).count() == 0:
        for name, description, keywords in DEFAULT_SERVICES:
            db.add(ServicePortfolio(
                name=name,
                description=description,
                keywords=keywords,
                target_buyers=["CIO", "CTO", "Head of Data", "Procurement"],
            ))

    existing = {x.name for x in db.query(DiscoverySource).all()}
    if "Global Web Search" not in existing:
        db.add(DiscoverySource(name="Global Web Search", source_type="WEB_SEARCH", base_url="https://www.bing.com", countries=["Global"]))
    for name, base_url, countries in PUBLIC_SOURCES:
        if name not in existing:
            db.add(DiscoverySource(name=name, source_type="WEB_SEARCH", base_url=base_url, countries=countries))
    db.commit()


def queries(db: Session, limit=30):
    seed_defaults(db)
    qs = []
    for portfolio in db.query(ServicePortfolio).filter(ServicePortfolio.active.is_(True)).all():
        terms = (portfolio.keywords or [])[:5] or [portfolio.name]
        for term in terms:
            qs.extend([
                f'"{term}" RFP OR tender OR RFQ',
                f'"{term}" "implementation partner"',
                f'"{term}" procurement',
                f'"{term}" supplier framework',
            ])

    from app.models.intelligence import CountryTarget
    countries = db.query(CountryTarget).filter(CountryTarget.enabled.is_(True)).order_by(CountryTarget.priority.desc()).all()
    if db.query(CountryTarget).count() and not countries:
        return []
    if countries:
        qs = [f'{q} "{country.name}" {" ".join(country.keywords or [])}' for q in qs for country in countries]

    unique = list(dict.fromkeys(qs))
    return unique[:limit] if limit is not None else unique


def _serper(query: str):
    if not settings.serper_api_key:
        return []
    with httpx.Client(timeout=25) as client:
        response = client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
            json={"q": query, "num": 10},
        )
        response.raise_for_status()
        data = response.json()
    return [
        {"title": row.get("title", ""), "url": row.get("link", ""), "description": row.get("snippet", ""), "source": "Google Web Search"}
        for row in data.get("organic", [])
    ]


def _bing_rss(query: str):
    """Keyless public-search fallback. Results are still treated only as discovery hints."""
    url = f"https://www.bing.com/search?format=rss&q={quote_plus(query)}"
    raw = public_get(url).text
    root = ET.fromstring(raw)
    out = []
    for item in root.findall(".//item")[:10]:
        out.append({
            "title": item.findtext("title") or "",
            "url": item.findtext("link") or "",
            "description": re.sub("<[^>]+>", " ", html.unescape(item.findtext("description") or "")),
            "source": "Bing Public Search",
        })
    return out


def _rss(url: str, name: str):
    raw = public_get(url).text
    root = ET.fromstring(raw)
    out = []
    for item in root.findall(".//item")[:50]:
        out.append({
            "title": item.findtext("title") or "",
            "url": item.findtext("link") or "",
            "description": re.sub("<[^>]+>", " ", html.unescape(item.findtext("description") or "")),
            "source": name,
        })
    if not out:
        ns = "{http://www.w3.org/2005/Atom}"
        for item in root.findall(f".//{ns}entry")[:50]:
            link = item.find(f"{ns}link")
            out.append({
                "title": item.findtext(f"{ns}title") or "",
                "url": link.attrib.get("href", "") if link is not None else "",
                "description": item.findtext(f"{ns}summary") or "",
                "source": name,
            })
    return out


def _website(url: str, name: str):
    text = public_get(url).text
    title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    clean = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", text))[:12000]
    return [{
        "title": html.unescape(title.group(1)).strip() if title else name,
        "url": url,
        "description": clean[:1500],
        "source": name,
    }]


def match(db: Session, text: str):
    low = text.lower()
    matches, evidence = [], []
    for portfolio in db.query(ServicePortfolio).filter(ServicePortfolio.active.is_(True)).all():
        hits = [k for k in (portfolio.keywords or []) if k.lower() in low]
        if hits:
            matches.append(portfolio.name)
            evidence.extend(hits)
    intent_hits = [
        x for x in [
            "rfp", "tender", "rfq", "procurement", "request for proposal",
            "implementation partner", "supplier", "framework agreement", "request for quotation",
        ] if x in low
    ]
    score = min(100, 20 + len(set(evidence)) * 10 + len(intent_hits) * 12) if matches and intent_hits else min(55, len(set(evidence)) * 10)
    return score, matches, list(dict.fromkeys(evidence)), intent_hits


def _normalize_url(url: str):
    parts = urlsplit(url)
    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        urlencode([(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")]),
        "",
    ))


def run_discovery(db: Session):
    # Demo mode now controls delivery simulation, not whether discovery must be synthetic.
    # Fixtures can still be explicitly requested for tests with DEMO_DISCOVERY_FIXTURES=true.
    if settings.demo_mode and os.getenv("DEMO_DISCOVERY_FIXTURES", "false").lower() in {"1", "true", "yes"}:
        from app.seed import seed_demo
        before = db.query(Opportunity).count()
        samples = seed_demo(db)
        return {
            "provider": "DEMO_FIXTURES",
            "queries_generated": 0,
            "raw_results": len(samples),
            "new_opportunities": db.query(Opportunity).count() - before,
            "qualified": 0,
            "errors": [],
            "demo_data_used": True,
        }

    seed_defaults(db)
    raw, errors = [], []
    from app.models.sales_agent import DiscoverySearchState
    all_queries = queries(db, limit=None)
    state = db.get(DiscoverySearchState, "global") or DiscoverySearchState(id="global", query_offset=0)
    offset = state.query_offset % len(all_queries) if all_queries else 0
    rotated = all_queries[offset:] + all_queries[:offset]
    qlist = rotated[:30]
    state.query_offset = (offset + len(qlist)) % len(all_queries) if all_queries else 0
    db.add(state)
    db.commit()

    for source in db.query(DiscoverySource).filter(DiscoverySource.active.is_(True)).all():
        try:
            if source.source_type == "WEB_SEARCH":
                domain = urlparse(source.base_url or "").hostname
                for query in qlist:
                    target = query
                    if source.countries and "Global" not in source.countries:
                        target += " " + " OR ".join(f'"{x}"' for x in source.countries)
                    if domain and domain not in {"google.serper.dev", "www.bing.com", "bing.com"}:
                        target = f"site:{domain} {target}"
                    rows = _serper(target) if settings.serper_api_key else _bing_rss(target)
                    raw.extend([{**row, "source": source.name, "query": target} for row in rows])
            elif source.source_type == "RSS" and source.base_url:
                raw.extend([{**x, "query": "RSS feed"} for x in _rss(source.base_url, source.name)])
            elif source.source_type == "WEBSITE" and source.base_url:
                raw.extend([{**x, "query": "Configured website scan"} for x in _website(source.base_url, source.name)])
        except Exception as exc:
            errors.append({"source": source.name, "message": str(exc)[:240]})

    created, qualified, seen = 0, 0, set()
    from app.models.intelligence import DiscoveryOccurrence

    for row in raw:
        url = (row.get("url") or "").strip()
        if not url:
            continue
        url = _normalize_url(url)
        if url in seen:
            continue
        seen.add(url)

        existing = db.query(Opportunity).filter(Opportunity.source_url == url).first()
        if not existing:
            existing = db.query(Opportunity).filter(
                func.lower(Opportunity.title) == (row.get("title") or "").strip().lower(),
                Opportunity.source_url.like(f'%{urlparse(url).netloc}%'),
            ).first()
        if existing:
            db.add(DiscoveryOccurrence(opportunity_id=existing.id, source_url=url, source_name=row.get("source", "Discovery")))
            continue

        text = f"{row.get('title', '')} {row.get('description', '')}"
        score, services, evidence, intents = match(db, text)
        if score < 45:
            continue

        host = urlparse(url).netloc.replace("www.", "") or row.get("source", "Unknown")
        company = db.query(Company).filter(Company.website == f"https://{host}").first()
        if not company:
            company = Company(name=host, website=f"https://{host}", country="Unknown", description=f"Discovered from {row.get('source')}")
            db.add(company)
            db.flush()

        opportunity = Opportunity(
            company_id=company.id,
            title=(row.get("title") or "Discovered opportunity")[:255],
            source_name=row.get("source", "Live Discovery"),
            source_url=url,
            country="Unknown",
            published_date=None,
            closing_date=None,
            description=(row.get("description") or "")[:6000],
            qualification_score=None,
            qualification_status="PENDING",
            business_fit=None,
            pipeline_status="DISCOVERED",
            matched_services=services,
            relevance_reason=(
                "Discovery relevance hint; structured qualification is pending. "
                f"Portfolio evidence: {', '.join(evidence[:8])}. "
                f"Buyer intent: {', '.join(intents[:5])}. "
                f"Discovery query: {row.get('query', '')}"
            ),
        )
        db.add(opportunity)
        db.flush()
        db.add(DiscoveryOccurrence(opportunity_id=opportunity.id, source_url=url, source_name=opportunity.source_name))
        created += 1

    db.commit()
    provider = "SERPER" if settings.serper_api_key else "BING_PUBLIC_SEARCH"
    result = {
        "provider": provider,
        "queries_generated": len(qlist),
        "raw_results": len(raw),
        "new_opportunities": created,
        "qualified": qualified,
        "errors": errors,
        "demo_data_used": False,
    }
    db.add(AgentRun(
        agent_name="Global Opportunity Discovery Agent",
        input_json={"queries": qlist[:10], "sources": [s.name for s in db.query(DiscoverySource).filter(DiscoverySource.active.is_(True)).all()]},
        output_json=result,
        status="SUCCESS" if raw or not errors else "WARNING",
    ))
    db.commit()
    return result
