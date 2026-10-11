# VTAB AI Sales Intelligence — DigitalOcean Linux deployment

Target host: existing Ubuntu 24.04 droplet for sales.vtabsquare.com.

## Safety defaults
- Keep `DEMO_MODE=true` during acceptance.
- Keep `SCHEDULER_ENABLED=false` until the API/UI and integrations are validated.
- Do not place secrets in GitHub. Store backend secrets in `/etc/vtab-sales/backend.env` with mode 600.
- Do not enable live customer sends until Microsoft 365, recipient verification and owner approval are validated.

## Install

```bash
sudo apt update
sudo apt install -y git nginx redis-server python3-venv python3-pip nodejs npm certbot python3-certbot-nginx
sudo useradd --system --create-home --shell /usr/sbin/nologin vtabsales || true
sudo mkdir -p /opt/vtab-sales /etc/vtab-sales
sudo chown -R vtabsales:vtabsales /opt/vtab-sales
sudo chmod 750 /etc/vtab-sales

sudo -u vtabsales git clone https://github.com/vtabsquare/VTAB-AI-Sales-Intelligence.git /opt/vtab-sales
cd /opt/vtab-sales/backend
sudo -u vtabsales python3 -m venv .venv
sudo -u vtabsales .venv/bin/pip install -r requirements.txt

cd /opt/vtab-sales/frontend
sudo -u vtabsales npm ci
sudo -u vtabsales cp .env.local.example .env.local
sudo -u vtabsales npm run build
```

Create `/etc/vtab-sales/backend.env` from `backend/.env.example`, using real private values. For initial acceptance set:

```env
APP_ENV=production
DEMO_MODE=true
SCHEDULER_ENABLED=false
MICROSOFT_SENDER_EMAIL=contactsales@vtabsquare.com
```

Then install services and Nginx:

```bash
sudo cp /opt/vtab-sales/deploy/linux/vtab-sales-backend.service /etc/systemd/system/
sudo cp /opt/vtab-sales/deploy/linux/vtab-sales-frontend.service /etc/systemd/system/
sudo cp /opt/vtab-sales/deploy/linux/vtab-sales-worker.service /etc/systemd/system/
sudo cp /opt/vtab-sales/deploy/linux/nginx-sales.vtabsquare.com.conf /etc/nginx/sites-available/sales.vtabsquare.com
sudo ln -sf /etc/nginx/sites-available/sales.vtabsquare.com /etc/nginx/sites-enabled/sales.vtabsquare.com
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable --now redis-server vtab-sales-backend vtab-sales-frontend
sudo systemctl disable --now vtab-sales-worker || true
sudo systemctl reload nginx
```

After DNS `sales.vtabsquare.com` points to the droplet:

```bash
sudo certbot --nginx -d sales.vtabsquare.com
```

## Acceptance

1. Open `https://sales.vtabsquare.com` and confirm the application loads.
2. Confirm the UI reports DEMO MODE.
3. Validate Neon connectivity and schema without destructive recreation.
4. Test Microsoft 365 connection and inbox sync with `Contactsales@vtabsquare.com`.
5. Run discovery manually and verify qualification/research/draft generation.
6. Verify no real email is sent in DEMO MODE.
7. Only after owner acceptance set `SCHEDULER_ENABLED=true`, restart backend/worker, and enable the worker:

```bash
sudo systemctl enable --now vtab-sales-worker
sudo systemctl restart vtab-sales-backend vtab-sales-worker
```

Keep final-send approval controls enabled for live outreach.
