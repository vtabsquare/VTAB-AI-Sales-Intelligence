"""Evidence extraction never guesses a mailbox or claims fetched content is verified."""

import re
from html import unescape
from urllib.parse import urljoin, urlparse

from app.services.public_http import public_get

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_LINK_RE = re.compile(r"href\s*=\s*[\"']([^\"'<>]+)[\"']", re.I)
_ALLOWED_HINTS = ("contact", "procurement", "tender", "supplier", "vendor", "rfp", "business", "about")
_BLOCKED_MAILBOX_FRAGMENTS = ("noreply", "no-reply", "donotreply", "do-not-reply", "example.com")


def _clean_html(raw: str):
    without_scripts = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", raw, flags=re.S | re.I)
    text = unescape(re.sub(r"<[^>]*>", " ", without_scripts))
    return re.sub(r"\s+", " ", text).strip()


def _emails(raw: str):
    values = []
    for candidate in _EMAIL_RE.findall(unescape(raw)):
        email = candidate.lower().strip(".,;:()[]{}<>")
        if any(fragment in email for fragment in _BLOCKED_MAILBOX_FRAGMENTS):
            continue
        if email not in values:
            values.append(email)
    return values


def _phones(raw: str):
    values = []
    for value in re.findall(r"href\s*=\s*[\"']tel:([^\"'<>]+)", raw, flags=re.I):
        value = value.strip()
        digits = re.sub(r"\D", "", value)
        if 7 <= len(digits) <= 15 and value not in values:
            values.append(value)
    return values


def fetch_evidence(url):
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.hostname.endswith((".local", ".invalid")):
        return {"status": "UNAVAILABLE", "source_url": url, "text": "", "emails": [], "phones": [], "pages_checked": []}

    try:
        response = public_get(url)
        canonical_url = str(response.url)
        raw = response.text[:500000]
        combined_text = [_clean_html(raw)]
        emails = _emails(raw)
        phones = _phones(raw)
        pages_checked = [canonical_url]

        # Follow only a small number of same-domain, publicly linked pages whose labels/URLs
        # strongly suggest procurement/contact evidence. No external enrichment and no guessing.
        host = urlparse(canonical_url).hostname
        candidates = []
        for href in _LINK_RE.findall(raw):
            absolute = urljoin(canonical_url, href)
            p = urlparse(absolute)
            if p.scheme not in {"http", "https"} or p.hostname != host:
                continue
            low = absolute.lower()
            if not any(hint in low for hint in _ALLOWED_HINTS):
                continue
            if absolute not in candidates and absolute != canonical_url:
                candidates.append(absolute)
            if len(candidates) >= 4:
                break

        for candidate in candidates:
            try:
                extra = public_get(candidate)
                extra_raw = extra.text[:300000]
                pages_checked.append(str(extra.url))
                combined_text.append(_clean_html(extra_raw))
                for email in _emails(extra_raw):
                    if email not in emails:
                        emails.append(email)
                for phone in _phones(extra_raw):
                    if phone not in phones:
                        phones.append(phone)
            except Exception:
                continue

        return {
            "status": "FETCHED",
            "source_url": canonical_url,
            "text": " ".join(combined_text)[:18000],
            "emails": emails[:20],
            "phones": phones[:20],
            "pages_checked": pages_checked[:5],
            "evidence_rule": "Published source evidence only; no mailbox guessing or inferred email patterns.",
        }
    except Exception:
        return {"status": "UNAVAILABLE", "source_url": url, "text": "", "emails": [], "phones": [], "pages_checked": []}
