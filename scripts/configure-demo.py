"""Generate local-only demo secrets. Never overwrite an existing environment."""
import secrets
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'.env'
if path.exists():
    raise SystemExit('An .env already exists. Preserve it and configure demo variables manually.')
password=secrets.token_urlsafe(18)
path.write_text(f'POSTGRES_PASSWORD={secrets.token_urlsafe(24)}\nLOGIN_EMAIL=demo@vtabsquare.local\nLOGIN_PASSWORD={password}\nJWT_SECRET={secrets.token_urlsafe(48)}\n')
path.chmod(0o600)
print('Created local .env. Sign in using LOGIN_EMAIL and LOGIN_PASSWORD from that file. Demo OTP: 123456.')
