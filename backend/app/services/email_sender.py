from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    """Raised when the outbound provider rejects or cannot process a message."""


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: str
    provider: str
    sender: str
    recipient: str
    demo_mode: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider": self.provider,
            "sender": self.sender,
            "recipient": self.recipient,
            "demo_mode": self.demo_mode,
        }


def _require_graph_configuration() -> None:
    missing = []

    if not settings.microsoft_tenant_id.strip():
        missing.append("MICROSOFT_TENANT_ID")
    if not settings.microsoft_client_id.strip():
        missing.append("MICROSOFT_CLIENT_ID")
    if not settings.microsoft_client_secret.strip():
        missing.append("MICROSOFT_CLIENT_SECRET")
    if not settings.microsoft_sender_email.strip():
        missing.append("MICROSOFT_SENDER_EMAIL")

    if missing:
        raise EmailDeliveryError(
            "Microsoft Graph is not configured. Missing: "
            + ", ".join(missing)
        )


def _get_graph_access_token(client: httpx.Client) -> str:
    token_url = (
        "https://login.microsoftonline.com/"
        f"{settings.microsoft_tenant_id.strip()}/oauth2/v2.0/token"
    )

    response = client.post(
        token_url,
        data={
            "client_id": settings.microsoft_client_id.strip(),
            "client_secret": settings.microsoft_client_secret.strip(),
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    if response.status_code >= 400:
        raise EmailDeliveryError(
            "Unable to obtain a Microsoft Graph access token. "
            f"HTTP {response.status_code}: {response.text[:500]}"
        )

    token = response.json().get("access_token")

    if not token:
        raise EmailDeliveryError(
            "Microsoft Graph token response did not contain an access token."
        )

    return token


def send_email(
    *,
    recipient_email: str,
    subject: str,
    body_text: str,
) -> dict[str, Any]:
    """
    Send one approved outreach email.

    DEMO_MODE=true:
        No network call is made. The send is simulated.

    DEMO_MODE=false:
        Uses Microsoft Graph application authentication and the configured
        Microsoft 365 sender mailbox.
    """

    recipient = recipient_email.strip()
    sender = settings.microsoft_sender_email.strip()

    if not recipient:
        raise EmailDeliveryError("Recipient email is required.")

    if settings.demo_mode:
        return EmailDeliveryResult(
            status="SIMULATED_SENT",
            provider="DEMO",
            sender=sender or "DEMO_SENDER",
            recipient=recipient,
            demo_mode=True,
        ).as_dict()

    _require_graph_configuration()

    timeout = httpx.Timeout(settings.graph_timeout_seconds)

    try:
        with httpx.Client(timeout=timeout) as client:
            access_token = _get_graph_access_token(client)

            encoded_sender = quote(sender, safe="")
            send_url = (
                "https://graph.microsoft.com/v1.0/users/"
                f"{encoded_sender}/sendMail"
            )

            response = client.post(
                send_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "message": {
                        "subject": subject,
                        "body": {
                            "contentType": "Text",
                            "content": body_text,
                        },
                        "toRecipients": [
                            {
                                "emailAddress": {
                                    "address": recipient,
                                }
                            }
                        ],
                    },
                    "saveToSentItems": True,
                },
            )

    except httpx.TimeoutException as exc:
        raise EmailDeliveryError(
            "Microsoft Graph request timed out."
        ) from exc
    except httpx.HTTPError as exc:
        raise EmailDeliveryError(
            f"Microsoft Graph network error: {exc}"
        ) from exc

    if response.status_code != 202:
        raise EmailDeliveryError(
            "Microsoft Graph rejected the send request. "
            f"HTTP {response.status_code}: {response.text[:1000]}"
        )

    return EmailDeliveryResult(
        status="GRAPH_ACCEPTED",
        provider="MICROSOFT_GRAPH",
        sender=sender,
        recipient=recipient,
        demo_mode=False,
    ).as_dict()
