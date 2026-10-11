#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vtab-sales-agent}"
BRANCH="${BRANCH:-feature/autonomous-web-agent}"

cd "$APP_DIR"
echo "[1/8] Updating source from $BRANCH"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "[2/8] Installing backend dependencies"
cd "$APP_DIR/backend"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "[3/8] Installing Playwright Chromium"
.venv/bin/python -m playwright install chromium
# Install browser OS libraries where supported; do not fail the deployment if apt metadata is restricted.
.venv/bin/python -m playwright install-deps chromium || true

echo "[4/8] Migrating database"
.venv/bin/alembic upgrade head

echo "[5/8] Building frontend"
cd "$APP_DIR/frontend"
npm ci
npm run build

echo "[6/8] Installing web-agent systemd service"
cp "$APP_DIR/deploy/linux/vtab-sales-web-agent.service" /etc/systemd/system/vtab-sales-web-agent.service
systemctl daemon-reload
systemctl enable vtab-sales-web-agent.service

echo "[7/8] Restarting VTAB Sales services"
systemctl restart vtab-sales-backend.service
systemctl restart vtab-sales-frontend.service
systemctl restart vtab-sales-worker.service || true
systemctl restart vtab-sales-web-agent.service

echo "[8/8] Health checks"
sleep 3
systemctl --no-pager --full status vtab-sales-web-agent.service | sed -n '1,18p' || true
curl -fsS http://127.0.0.1:8001/api/health || true
echo
echo "Autonomous Web Agent installed. Open https://sales.vtabsquare.com/web-agent"
