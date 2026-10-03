from urllib.parse import quote
import httpx
from fastapi import APIRouter, HTTPException
from app.core.config import settings

r = APIRouter(prefix="/api/integrations", tags=["integrations"])

def _missing():
    vals = {
        "MICROSOFT_TENANT_ID": settings.microsoft_tenant_id,
        "MICROSOFT_CLIENT_ID": settings.microsoft_client_id,
        "MICROSOFT_CLIENT_SECRET": settings.microsoft_client_secret,
        "MICROSOFT_SENDER_EMAIL": settings.microsoft_sender_email,
    }
    return [k for k, v in vals.items() if not (v or "").strip()]

def _graph_error(resp: httpx.Response) -> str:
    try:
        err = (resp.json() or {}).get("error") or {}
        return f"{err.get('code', 'GraphError')}: {err.get('message', 'Microsoft Graph request failed.')}"
    except Exception:
        return f"HTTP {resp.status_code}"

def _token(client: httpx.Client) -> str:
    token_url = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id.strip()}/oauth2/v2.0/token"
    tr = client.post(token_url, data={
        "client_id": settings.microsoft_client_id.strip(),
        "client_secret": settings.microsoft_client_secret.strip(),
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    })
    if tr.status_code >= 400:
        raise HTTPException(400, f"Token request failed: {_graph_error(tr)}")
    token = (tr.json() or {}).get("access_token")
    if not token:
        raise HTTPException(400, "Microsoft token response did not include an access token.")
    return token

@r.get("/microsoft/status")
def microsoft_status():
    missing = _missing()
    configured = not missing
    return {
        "provider": "MICROSOFT_GRAPH",
        "configured": configured,
        "demo_mode": settings.demo_mode,
        "sender": settings.microsoft_sender_email or None,
        "missing": missing,
        # DEMO_MODE blocks outbound delivery, but read-only inbox sync is intentionally allowed.
        "send_enabled": (not settings.demo_mode) and configured,
        "inbox_sync_enabled": configured,
        "inbox_sync_read_only": True,
    }

@r.post("/microsoft/test")
def microsoft_test():
    missing = _missing()
    if missing:
        raise HTTPException(400, "Missing Microsoft Graph configuration: " + ", ".join(missing))
    sender_email = settings.microsoft_sender_email.strip()
    sender = quote(sender_email, safe="")
    try:
        with httpx.Client(timeout=httpx.Timeout(settings.graph_timeout_seconds)) as client:
            token = _token(client)
            mr = client.get(
                f"https://graph.microsoft.com/v1.0/users/{sender}/mailFolders/inbox/messages",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                params={"$top": "1", "$select": "id,subject,receivedDateTime"},
            )
            if mr.status_code >= 400:
                raise HTTPException(400, f"Graph mailbox check failed: {_graph_error(mr)}")
            return {
                "connected": True,
                "provider": "MICROSOFT_GRAPH",
                "mailbox": {
                    "displayName": sender_email,
                    "mail": sender_email,
                    "userPrincipalName": sender_email,
                    "read_access": True,
                },
                "demo_mode": settings.demo_mode,
                "message": "Microsoft Graph authentication and read-only Outlook mailbox access succeeded.",
            }
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(400, f"Microsoft Graph connection error: {exc}")
