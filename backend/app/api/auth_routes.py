import base64
import hashlib
import hmac
import json
import secrets
import time

from datetime import datetime, timedelta
from urllib.parse import quote

import httpx

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, update

from app.core.config import settings
from app.models.db import SessionLocal
from app.models.platform import AuthOtpChallenge, AuthSession


r = APIRouter(prefix="/api/auth", tags=["auth"])


LOGIN_EMAIL = settings.login_email.strip().lower()
LOGIN_PASSWORD = settings.login_password


# ============================================================
# TOKEN HELPERS
# ============================================================

def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def make_token(email: str, minutes: int = 480) -> str:
    payload = {
        "sub": email,
        "jti": secrets.token_hex(16),
        "exp": int(time.time() + minutes * 60),
    }

    raw = _b64(
        json.dumps(
            payload,
            separators=(",", ":"),
        ).encode()
    )

    signature = _b64(
        hmac.new(
            settings.jwt_secret.encode(),
            raw.encode(),
            hashlib.sha256,
        ).digest()
    )

    token = raw + "." + signature
    with SessionLocal() as db:
        db.add(AuthSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), email=email,
                           expires_at=datetime.utcfromtimestamp(payload['exp']), revoked=False))
        db.commit()
    return token


def verify_token(token: str) -> bool:
    try:
        raw, signature = token.split(".", 1)

        expected = _b64(
            hmac.new(
                settings.jwt_secret.encode(),
                raw.encode(),
                hashlib.sha256,
            ).digest()
        )

        if not hmac.compare_digest(signature, expected):
            return False

        payload = json.loads(
            base64.urlsafe_b64decode(
                raw + "=" * (-len(raw) % 4)
            )
        )

        if payload.get("sub") != LOGIN_EMAIL or int(payload.get("exp", 0)) <= time.time():
            return False
        with SessionLocal() as db:
            active = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
            return bool(active and not active.revoked and active.expires_at > datetime.utcnow())

    except Exception:
        return False


# ============================================================
# OTP HELPERS
# ============================================================

def hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def create_otp_challenge(email: str, code: str) -> None:
    """
    Invalidates previous unused OTPs and stores the new OTP hash.
    The actual OTP is never stored in SQL Server.
    """

    db = SessionLocal()

    try:
        # Invalidate any previous active OTPs for this user.
        db.execute(
            update(AuthOtpChallenge)
            .where(
                AuthOtpChallenge.email == email,
                AuthOtpChallenge.used == False,  # noqa: E712
            )
            .values(used=True)
        )

        challenge = AuthOtpChallenge(
            email=email,
            otp_hash=hash_otp(code),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            attempt_count=0,
            used=False,
        )

        db.add(challenge)
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def delete_otp_challenge(email: str, code: str) -> None:
    """
    Used when Microsoft Graph fails to send the OTP.
    Marks the just-created OTP unusable.
    """

    db = SessionLocal()

    try:
        challenge = db.execute(
            select(AuthOtpChallenge)
            .where(
                AuthOtpChallenge.email == email,
                AuthOtpChallenge.otp_hash == hash_otp(code),
                AuthOtpChallenge.used == False,  # noqa: E712
            )
            .order_by(AuthOtpChallenge.created_at.desc())
        ).scalars().first()

        if challenge:
            challenge.used = True
            db.commit()

    except Exception:
        db.rollback()

    finally:
        db.close()


# ============================================================
# MICROSOFT GRAPH
# ============================================================

def _graph_token(client: httpx.Client) -> str:
    response = client.post(
        (
            f"https://login.microsoftonline.com/"
            f"{settings.microsoft_tenant_id}/oauth2/v2.0/token"
        ),
        data={
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
    )

    response.raise_for_status()

    return response.json()["access_token"]


def send_otp(code: str) -> None:
    if settings.demo_auth:
        if not settings.demo_mode or settings.app_env not in {'development','local','test'}:
            raise RuntimeError('Demo authentication is forbidden outside development demo mode.')
        return
    required = [
        settings.microsoft_tenant_id,
        settings.microsoft_client_id,
        settings.microsoft_client_secret,
        settings.microsoft_sender_email,
    ]

    if not all(required):
        raise RuntimeError(
            "Microsoft Graph configuration is incomplete."
        )

    html = f"""
    <div style="
        font-family:Segoe UI,Arial,sans-serif;
        background:#f4f7fb;
        padding:40px;
    ">
        <div style="
            max-width:560px;
            margin:auto;
            background:#ffffff;
            border:1px solid #dbe4f0;
            padding:40px;
        ">

            <div style="
                font-size:12px;
                letter-spacing:2px;
                color:#3157d5;
                font-weight:700;
            ">
                VTAB AI SALES INTELLIGENCE
            </div>

            <h2 style="
                color:#0b1f3a;
                margin-top:24px;
            ">
                Your sign-in verification code
            </h2>

            <p style="
                color:#53657d;
                line-height:1.6;
            ">
                Use this one-time code to complete your secure
                sign-in. It expires in 10 minutes.
            </p>

            <div style="
                font-size:36px;
                letter-spacing:12px;
                font-weight:800;
                color:#173b8f;
                padding:24px 0;
            ">
                {code}
            </div>

            <p style="
                font-size:12px;
                color:#7b8ba1;
            ">
                If you did not initiate this sign-in,
                do not share this code.
            </p>

        </div>
    </div>
    """

    with httpx.Client(timeout=30) as client:

        token = _graph_token(client)

        sender = quote(
            settings.microsoft_sender_email,
            safe="",
        )

        response = client.post(
            (
                "https://graph.microsoft.com/v1.0/"
                f"users/{sender}/sendMail"
            ),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "message": {
                    "subject": (
                        f"{code} · VTAB sign-in verification"
                    ),
                    "body": {
                        "contentType": "HTML",
                        "content": html,
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": LOGIN_EMAIL
                            }
                        }
                    ],
                },
                "saveToSentItems": True,
            },
        )

        response.raise_for_status()


# ============================================================
# REQUEST MODELS
# ============================================================

class Login(BaseModel):
    email: str
    password: str


class Verify(BaseModel):
    email: str
    code: str


# ============================================================
# LOGIN
# ============================================================

@r.post("/login")
def login(payload: Login):

    email = payload.email.strip().lower()

    if (
        email != LOGIN_EMAIL
        or not hmac.compare_digest(payload.password.encode(), LOGIN_PASSWORD.encode())
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    if not LOGIN_PASSWORD or not settings.jwt_secret or settings.jwt_secret == 'change-me-before-production':
        raise HTTPException(503, 'Configure LOGIN_PASSWORD and a private JWT_SECRET before signing in.')
    with SessionLocal() as db:
        recent = db.execute(select(AuthOtpChallenge).where(
            AuthOtpChallenge.email == email,
            AuthOtpChallenge.created_at > datetime.utcnow() - timedelta(seconds=60)
        )).scalars().first()
        if recent:
            raise HTTPException(429, 'Please wait one minute before requesting another verification email.')
    # Generate secure six-digit OTP.
    code = settings.demo_otp if settings.demo_auth and settings.demo_mode and settings.app_env in {"development","local","test"} else f"{secrets.randbelow(1000000):06d}"

    try:
        # Save OTP hash BEFORE sending the email.
        create_otp_challenge(
            email=LOGIN_EMAIL,
            code=code,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create verification challenge: "
                "Check the server configuration and connection."
            ),
        )

    try:
        send_otp(code)

    except Exception as exc:

        # Do not leave a usable OTP if email delivery failed.
        delete_otp_challenge(
            email=LOGIN_EMAIL,
            code=code,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Password accepted, but the verification "
                "email could not be sent: "
                "Check the server configuration and connection."
            ),
        )

    return {
        "status": "OTP_SENT",
        "demo_auth": settings.demo_auth,
        "message": "Development demo: use the configured DEMO_OTP (default 123456). No verification email was sent." if settings.demo_auth else "A verification code has been sent to your Microsoft 365 mailbox.",
        "email": LOGIN_EMAIL,
        "expires_minutes": 10,
    }


# ============================================================
# VERIFY OTP
# ============================================================

@r.post("/verify")
def verify(payload: Verify):

    email = payload.email.strip().lower()
    code = payload.code.strip()

    if email != LOGIN_EMAIL:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication request.",
        )

    if len(code) != 6 or not code.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Enter the six-digit verification code.",
        )

    db = SessionLocal()

    try:

        challenge = db.execute(
            select(AuthOtpChallenge)
            .where(
                AuthOtpChallenge.email == email,
                AuthOtpChallenge.used == False,  # noqa: E712
            )
            .order_by(
                AuthOtpChallenge.created_at.desc()
            )
        ).scalars().first()

        if not challenge:
            raise HTTPException(
                status_code=400,
                detail="Request a new verification code.",
            )

        # ----------------------------------------------------
        # Check expiry
        # ----------------------------------------------------

        if datetime.utcnow() > challenge.expires_at:

            challenge.used = True
            db.commit()

            raise HTTPException(
                status_code=400,
                detail="Verification code expired. Request a new code.",
            )

        # ----------------------------------------------------
        # Attempt limit
        # ----------------------------------------------------

        attempted=db.execute(update(AuthOtpChallenge).where(
            AuthOtpChallenge.id==challenge.id, AuthOtpChallenge.used==False,
            AuthOtpChallenge.attempt_count<5
        ).values(attempt_count=AuthOtpChallenge.attempt_count+1))
        if attempted.rowcount != 1:
            db.execute(update(AuthOtpChallenge).where(AuthOtpChallenge.id==challenge.id).values(used=True))
            db.commit()
            raise HTTPException(429, 'Too many verification attempts. Request a new code.')

        # ----------------------------------------------------
        # Verify OTP
        # ----------------------------------------------------

        supplied_hash = hash_otp(code)

        if not hmac.compare_digest(
            challenge.otp_hash,
            supplied_hash,
        ):

            db.commit()

            raise HTTPException(
                status_code=401,
                detail="Incorrect verification code.",
            )

        # ----------------------------------------------------
        # OTP accepted
        # ----------------------------------------------------

        claimed = db.execute(update(AuthOtpChallenge).where(
            AuthOtpChallenge.id == challenge.id, AuthOtpChallenge.used == False,
            AuthOtpChallenge.expires_at > datetime.utcnow()
        ).values(used=True))
        if claimed.rowcount != 1:
            db.rollback()
            raise HTTPException(409, 'Verification code was already used. Request a new code.')
        db.commit()

        token = make_token(email)

        return {
            "status": "AUTHENTICATED",
            "token": token,
            "user": {
                "email": email,
                "name": "VTAB Sales",
            },
        }

    except HTTPException:
        raise

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Verification failed because of a server error: "
                "Check the server configuration and connection."
            ),
        )

    finally:
        db.close()


# ============================================================
# SESSION
# ============================================================

@r.get("/session")
def session(request: Request):

    auth = request.headers.get(
        "authorization",
        "",
    )

    token = (
        auth[7:]
        if auth.lower().startswith("bearer ")
        else ""
    )

    authenticated = verify_token(token)

    return {
        "authenticated": authenticated,
        "email": LOGIN_EMAIL if authenticated else None,
        "face_recognition": {
            "enabled": False,
            "status": "OPTIONAL_NOT_CONFIGURED",
        },
    }


# ============================================================
# LOGOUT
# ============================================================

@r.post("/logout")
def logout(request: Request):
    auth = request.headers.get('authorization', '')
    token = auth[7:] if auth.lower().startswith('bearer ') else ''
    with SessionLocal() as db:
        row = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
        if row:
            row.revoked = True
            db.commit()


    return {
        "status": "SIGNED_OUT",
    }