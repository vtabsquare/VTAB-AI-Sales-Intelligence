#!/usr/bin/env bash
set -euo pipefail

APP=/opt/vtab-sales-agent
BACKEND="$APP/backend"
FRONTEND="$APP/frontend"
ENV1=/etc/vtab-sales/backend.env
ENV2="$BACKEND/.env"
STAMP=$(date +%Y%m%d-%H%M%S)

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "Run this script as root on the VTAB DigitalOcean droplet."
  exit 1
fi

cd "$APP"
git config --global --add safe.directory "$APP" >/dev/null 2>&1 || true

echo "===== VTAB AI Sales Intelligence · Production Finalizer ====="
echo "This script keeps all outbound activity human-controlled."
echo

echo "1/10  Pull latest application code"
git fetch origin
git checkout origin/main -- .

echo "2/10  Backup current environment"
cp "$ENV1" "$ENV1.backup.$STAMP"
cp "$ENV2" "$ENV2.backup.$STAMP"

echo
cat <<'TXT'
IMPORTANT SECURITY STEP
Before continuing, rotate the provider-side credentials that were previously exposed:
  • Neon database role password / connection string
  • Microsoft Entra application client secret
Then paste ONLY the newly rotated values below. Input is hidden.
TXT

read -r -s -p "NEW Neon DATABASE_URL: " NEW_DB; echo
read -r -s -p "NEW Microsoft client secret: " NEW_MS_SECRET; echo
read -r -s -p "NEW application login password (10-16 chars recommended): " NEW_LOGIN_PASSWORD; echo

if [[ -z "$NEW_DB" || -z "$NEW_MS_SECRET" || -z "$NEW_LOGIN_PASSWORD" ]]; then
  echo "Required rotated values were not provided. No go-live changes were made."
  exit 2
fi

NEW_JWT=$(openssl rand -hex 32)
export NEW_DB NEW_MS_SECRET NEW_LOGIN_PASSWORD NEW_JWT

echo "3/10  Update protected environment files"
python3 - <<'PY'
from pathlib import Path
import os

paths=[Path('/etc/vtab-sales/backend.env'),Path('/opt/vtab-sales-agent/backend/.env')]
values={
 'APP_ENV':'production',
 'DATABASE_URL':os.environ['NEW_DB'],
 'MICROSOFT_CLIENT_SECRET':os.environ['NEW_MS_SECRET'],
 'LOGIN_PASSWORD':os.environ['NEW_LOGIN_PASSWORD'],
 'JWT_SECRET':os.environ['NEW_JWT'],
 'DEMO_MODE':'true',
 'SCHEDULER_ENABLED':'false',
 'INITIALIZE_SCHEMA':'false',
}
for p in paths:
    rows=p.read_text().splitlines() if p.exists() else []
    out=[]; seen=set()
    for line in rows:
        key=line.split('=',1)[0].strip() if '=' in line else ''
        if key in values:
            out.append(f'{key}={values[key]}'); seen.add(key)
        else:
            out.append(line)
    for key,value in values.items():
        if key not in seen: out.append(f'{key}={value}')
    p.write_text('\n'.join(out)+'\n')
PY
chmod 640 "$ENV1"
chmod 600 "$ENV2"
unset NEW_DB NEW_MS_SECRET NEW_LOGIN_PASSWORD NEW_JWT

echo "4/10  Validate Python"
cd "$BACKEND"
.venv/bin/python -m py_compile \
  app/main.py \
  app/api/outreach_guardrails_routes.py \
  app/api/policy_guardrails_routes.py \
  app/services/global_discovery.py \
  app/services/source_evidence.py

echo "5/10  Seed real public discovery sources"
.venv/bin/python - <<'PY'
from app.models.db import SessionLocal
from app.services.global_discovery import seed_defaults

db=SessionLocal()
try:
    seed_defaults(db)
    from app.models.platform import DiscoverySource
    print('Enabled discovery sources:')
    for s in db.query(DiscoverySource).filter(DiscoverySource.active.is_(True)).order_by(DiscoverySource.name):
        print(' -',s.name,'|',s.base_url)
finally:
    db.close()
PY

echo "6/10  Build premium frontend"
cd "$FRONTEND"
npm run build

echo "7/10  Restart application in SAFE DEMO delivery mode"
systemctl restart vtab-sales-backend
systemctl restart vtab-sales-frontend
systemctl restart vtab-sales-worker
sleep 6

systemctl is-active --quiet vtab-sales-backend
systemctl is-active --quiet vtab-sales-frontend
systemctl is-active --quiet vtab-sales-worker
curl -fsS https://sales.vtabsquare.com/backend-api/health >/dev/null

echo "8/10  Run one real-public-source discovery cycle while sends remain simulated"
cd "$BACKEND"
.venv/bin/python - <<'PY'
from app.models.db import SessionLocal
from app.services.global_discovery import run_discovery

db=SessionLocal()
try:
    result=run_discovery(db)
    print('Discovery provider:',result.get('provider'))
    print('Queries:',result.get('queries_generated'))
    print('Raw results:',result.get('raw_results'))
    print('New opportunities:',result.get('new_opportunities'))
    print('Errors:',len(result.get('errors') or []))
finally:
    db.close()
PY

echo "9/10  Verify governance and secret readiness"
.venv/bin/python - <<'PY'
from app.core.config import settings
from app.models.db import SessionLocal
from app.services.sales_manager import policy_for

checks={
 'Database is remote': bool(settings.database_url and 'localhost/vtab_sales' not in settings.database_url),
 'Microsoft Graph configured': bool(settings.microsoft_tenant_id and settings.microsoft_client_id and settings.microsoft_client_secret and settings.microsoft_sender_email),
 'Sender is Contactsales@vtabsquare.com': settings.microsoft_sender_email.lower().strip()=='contactsales@vtabsquare.com',
 'JWT length >= 32': len(settings.jwt_secret or '')>=32,
 'Login configured': bool(settings.login_email and settings.login_password),
}
db=SessionLocal()
try:
    policy=policy_for(db)
    policy.auto_initial_outreach=False
    policy.auto_acknowledge=False
    db.commit()
    checks['Automatic initial outreach disabled']=not policy.auto_initial_outreach
    checks['Automatic acknowledgement disabled']=not policy.auto_acknowledge
finally:
    db.close()
for k,v in checks.items(): print(('PASS' if v else 'FAIL'),'-',k)
if not all(checks.values()): raise SystemExit('Readiness check failed. DEMO_MODE remains true.')
PY

echo
echo "All automated checks passed."
echo "Human approval remains mandatory; automatic initial outreach is disabled by code."
echo
read -r -p "Type GO LIVE to switch DEMO_MODE=false now, or press Enter to remain in safe demo mode: " DECISION
if [[ "$DECISION" == "GO LIVE" ]]; then
  echo "10/10 Switch to controlled LIVE mode"
  for f in "$ENV1" "$ENV2"; do
    sed -i 's/^DEMO_MODE=.*/DEMO_MODE=false/' "$f"
    sed -i 's/^SCHEDULER_ENABLED=.*/SCHEDULER_ENABLED=false/' "$f"
  done
  systemctl restart vtab-sales-backend
  systemctl restart vtab-sales-worker
  sleep 5
  curl -fsS https://sales.vtabsquare.com/backend-api/health >/dev/null
  echo "LIVE MODE ENABLED — delivery still requires human approval + explicit Send Center confirmation."
else
  echo "SAFE DEMO MODE RETAINED. Real public discovery is enabled; outbound delivery remains simulated."
fi

echo
echo "===== FINAL STATUS ====="
systemctl --no-pager --full status vtab-sales-backend | sed -n '1,8p'
systemctl --no-pager --full status vtab-sales-frontend | sed -n '1,8p'
systemctl --no-pager --full status vtab-sales-worker | sed -n '1,8p'
echo "Open: https://sales.vtabsquare.com"
