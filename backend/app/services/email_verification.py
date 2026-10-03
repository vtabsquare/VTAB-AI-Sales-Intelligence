from __future__ import annotations

from email_validator import EmailNotValidError, validate_email
import dns.resolver


def verify_email_address(email: str) -> dict:
    """Validate syntax and the recipient domain/MX.

    This deliberately does NOT claim that the individual mailbox exists.
    A successful MX check returns DOMAIN_VALID, not VERIFIED.
    """
    try:
        info = validate_email(email, check_deliverability=False)
        normalized = info.normalized
        domain = normalized.rsplit("@", 1)[1]
    except EmailNotValidError as exc:
        return {
            "status": "INVALID",
            "normalized_email": None,
            "syntax_valid": False,
            "domain_valid": False,
            "mx_found": False,
            "mx_hosts": [],
            "message": str(exc),
        }

    try:
        answers = dns.resolver.resolve(domain, "MX")
        hosts = sorted({str(x.exchange).rstrip(".") for x in answers})
        if not hosts:
            raise dns.resolver.NoAnswer()
        return {
            "status": "DOMAIN_VALID",
            "normalized_email": normalized,
            "syntax_valid": True,
            "domain_valid": True,
            "mx_found": True,
            "mx_hosts": hosts,
            "message": (
                "Email syntax and domain MX are valid. "
                "This does not prove that the individual mailbox exists."
            ),
        }
    except Exception as exc:
        return {
            "status": "DOMAIN_INVALID",
            "normalized_email": normalized,
            "syntax_valid": True,
            "domain_valid": False,
            "mx_found": False,
            "mx_hosts": [],
            "message": f"No usable MX record was found for {domain}: {exc}",
        }
