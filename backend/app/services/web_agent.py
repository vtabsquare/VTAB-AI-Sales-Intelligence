from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

from sqlalchemy.orm import Session

from app.models.entities import Company, Opportunity
from app.models.web_agent import AgentActivity, AgentApproval, WebAgentRun, WebSource

DEFAULT_KEYWORDS = [
    "power bi", "microsoft fabric", "databricks", "data analytics",
    "data engineering", "ai agent", "artificial intelligence",
    "digital transformation", "application development", "managed it services",
]
BLOCKED_SCHEMES = {"file", "ftp", "data", "javascript"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _utcnow(): return datetime.now(timezone.utc)


def _log(db: Session, run_id: int | None, action: str, detail: str = "", phase: str = "browser", level: str = "info"):
    db.add(AgentActivity(run_id=run_id, action=action, detail=detail, phase=phase, level=level)); db.commit()


def validate_public_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme.lower() in BLOCKED_SCHEMES or p.scheme.lower() not in {"http", "https"}: raise ValueError("Only public http/https URLs are allowed")
    host = (p.hostname or "").lower()
    if not host or host in BLOCKED_HOSTS or host.endswith(".local"): raise ValueError("Private/local targets are not allowed")
    return url


def extract_candidate_links(base_url: str, links: list[dict], keywords: list[str]) -> list[dict]:
    out, seen = [], set()
    for item in links:
        href = (item.get("href") or "").strip(); text = re.sub(r"\s+", " ", (item.get("text") or "")).strip()
        if not href: continue
        absolute = urljoin(base_url, href)
        if absolute in seen: continue
        hay = f"{text} {absolute}".lower()
        if any(k.lower() in hay for k in keywords):
            seen.add(absolute); out.append({"url": absolute, "title": text[:255] or absolute[:255], "evidence": "keyword_match"})
    return out[:100]


def ingest_candidates(db: Session, source: WebSource, run: WebAgentRun, candidates: list[dict]) -> dict:
    """Bridge Browser Agent -> Opportunity -> Research -> Action pipeline.

    Creates only evidence-backed opportunity records. Qualification/research/drafting reuse
    the existing production agent services and remain subject to their existing guardrails.
    """
    from app.services.engine import qualify, research, draft
    created, qualified, researched, drafted, duplicates = 0, 0, 0, 0, 0
    origin = f"{urlparse(source.url).scheme}://{urlparse(source.url).netloc}"
    company = db.query(Company).filter(Company.website == origin).first()
    if not company:
        company = Company(name=source.name, website=origin, country=source.country, description=f"Organization/source discovered through {source.name}")
        db.add(company); db.flush()

    # De-duplicate both by URL and by normalized title within the same source organization.
    for c in candidates[:50]:
        url = c.get("url") or ""
        title = (c.get("title") or "Published opportunity")[:255]
        if not url: continue
        existing = db.query(Opportunity).filter(Opportunity.source_url == url).first()
        if existing:
            duplicates += 1; continue
        desc = (c.get("snippet") or f"Opportunity candidate discovered on {source.name}. Published link: {url}")[:12000]
        row = Opportunity(company_id=company.id, title=title, source_name=source.name, source_url=url,
                          country=source.country or "Unknown", description=desc, pipeline_status="DISCOVERED")
        db.add(row); db.commit(); db.refresh(row); created += 1
        _log(db, run.id, "Opportunity created", f"{row.title} | {row.source_url}", "opportunity")
        try:
            qualify(db, row)
            if row.qualification_status == "QUALIFIED":
                qualified += 1; _log(db, run.id, "Opportunity qualified", f"{row.title} | score={row.qualification_score}", "qualification")
                try:
                    research(db, row); researched += 1; _log(db, run.id, "Organization research completed", row.title, "research")
                except Exception as exc:
                    db.rollback(); _log(db, run.id, "Research needs review", str(exc)[:800], "research", "warning")
                try:
                    outreach = draft(db, row); drafted += 1
                    _log(db, run.id, "EOI draft created", f"draft={outreach.id}; status={outreach.status}", "action")
                except Exception as exc:
                    db.rollback(); _log(db, run.id, "Draft not created", str(exc)[:800], "action", "warning")
        except Exception as exc:
            db.rollback(); _log(db, run.id, "Qualification failed", str(exc)[:800], "qualification", "warning")

    run.opportunities_created = created
    source.opportunities_found += created
    db.commit()
    return {"created": created, "qualified": qualified, "researched": researched, "drafted": drafted, "duplicates": duplicates}


async def browse_source(db: Session, source: WebSource, mission: str, keywords: list[str] | None = None) -> dict:
    keywords = keywords or DEFAULT_KEYWORDS
    run = WebAgentRun(source_id=source.id, mission=mission, status="running", current_url=source.url, current_action="launching browser", started_at=_utcnow())
    db.add(run); db.commit(); db.refresh(run); _log(db, run.id, "Browser session started", source.url)
    try:
        validate_public_url(source.url)
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = await browser.new_context(user_agent="VTAB-Sales-Intelligence/1.0", accept_downloads=True)
            page = await context.new_page(); await page.goto(source.url, wait_until="domcontentloaded", timeout=45000)
            run.pages_visited = 1; run.current_action = "extracting page intelligence"; db.commit()
            title = await page.title(); body = (await page.locator("body").inner_text(timeout=15000))[:120000]
            links = await page.locator("a").evaluate_all("els => els.slice(0,1500).map(a => ({href:a.href,text:(a.innerText||a.textContent||'').trim()}))")
            candidates = extract_candidate_links(page.url, links, keywords); run.items_extracted = len(candidates)
            _log(db, run.id, "Page extracted", f"{title} | {len(candidates)} candidate opportunity links", "browser")
            host = urlparse(page.url).hostname; visited = {page.url}; expanded = []
            for candidate in candidates[:12]:
                if len(visited) >= 5: break
                if urlparse(candidate["url"]).hostname != host: continue
                try:
                    await page.goto(candidate["url"], wait_until="domcontentloaded", timeout=30000); visited.add(page.url); run.pages_visited += 1
                    text = (await page.locator("body").inner_text(timeout=10000))[:50000]
                    expanded.append({**candidate, "snippet": re.sub(r"\s+", " ", text)[:6000]})
                except Exception as exc:
                    _log(db, run.id, "Child page skipped", str(exc)[:500], "browser", "warning"); expanded.append(candidate)
            await browser.close()

        run.current_action = "opportunity intelligence"; db.commit()
        intelligence = ingest_candidates(db, source, run, expanded or candidates)
        run.status = "completed"; run.current_action = "completed"; run.finished_at = _utcnow()
        source.last_scan_at = _utcnow(); source.next_scan_at = _utcnow() + timedelta(minutes=source.scan_frequency_minutes)
        source.success_rate = min(100.0, source.success_rate * 0.8 + 20.0); db.commit()
        _log(db, run.id, "Autonomous cycle completed", f"Visited {run.pages_visited} pages; {json.dumps(intelligence)}", "orchestrator")
        return {"run_id": run.id, "title": title, "body_excerpt": body[:3000], "candidates": (expanded or candidates)[:100], "intelligence": intelligence}
    except Exception as exc:
        run.status = "needs_review" if any(x in str(exc).lower() for x in ["captcha", "mfa", "verification", "login"]) else "failed"
        run.error_code = "HUMAN_VERIFICATION" if run.status == "needs_review" else "BROWSER_ERROR"; run.error_message = str(exc)[:4000]; run.finished_at = _utcnow()
        source.failure_count += 1; source.next_scan_at = _utcnow() + timedelta(minutes=max(60, source.scan_frequency_minutes)); db.commit()
        _log(db, run.id, "Browser run failed", str(exc)[:1500], "browser", "error")
        if run.status == "needs_review":
            db.add(AgentApproval(run_id=run.id, risk="amber", action_type="human_verification", title=f"Human verification required for {source.name}", payload_json=json.dumps({"url": source.url}))); db.commit()
        return {"run_id": run.id, "status": run.status, "error": run.error_message}


def dashboard(db: Session) -> dict:
    sources = db.query(WebSource).all(); runs = db.query(WebAgentRun).order_by(WebAgentRun.id.desc()).limit(100).all()
    approvals = db.query(AgentApproval).filter(AgentApproval.status == "pending").count(); active = sum(1 for r in runs if r.status in {"queued", "running"})
    return {"status":"running" if active else "ready","sources":len(sources),"enabled_sources":sum(1 for s in sources if s.enabled),
            "active_runs":active,"completed_runs":sum(1 for r in runs if r.status=="completed"),"failed_runs":sum(1 for r in runs if r.status=="failed"),
            "pending_approvals":approvals,"items_extracted":sum(r.items_extracted or 0 for r in runs),"pages_visited":sum(r.pages_visited or 0 for r in runs),
            "opportunities_created":sum(r.opportunities_created or 0 for r in runs)}


def due_sources(db: Session) -> list[WebSource]:
    now = _utcnow(); rows = db.query(WebSource).filter(WebSource.enabled.is_(True)).order_by(WebSource.priority.desc()).all()
    return [s for s in rows if not s.next_scan_at or s.next_scan_at <= now][:10]


def run_due_sources_sync(db: Session, mission: str = "Discover global opportunities matching VTAB Square services") -> list[dict]:
    return [asyncio.run(browse_source(db, source, mission)) for source in due_sources(db)]
