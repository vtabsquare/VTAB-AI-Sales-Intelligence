# VTAB Autonomous Sales & Website Intelligence Agent

This upgrade extends the existing production application; it does not replace Sales Intelligence, Discovery, Pipeline, Response Center, Sales Manager, or current outreach guardrails.

## Included

1. Browser Agent: Playwright Chromium, navigation/extraction, bounded same-host traversal, failure classification, public-URL protection.
2. Opportunity Agent: evidence-backed opportunity creation, URL de-duplication, existing VTAB qualification engine reuse.
3. Research Agent: existing organization/contact evidence pipeline invoked for qualified opportunities.
4. Action Agent: EOI drafts generated through existing approved-knowledge/recipient guardrails. Sending remains human-controlled by default.
5. Autonomous Agent: independent DigitalOcean systemd worker polls configured sources and runs due scans continuously.
6. Command Center: `/web-agent` shows sources, runs, extraction metrics and decision/activity trace.
7. Approval: CAPTCHA/MFA/login challenges are escalated, never bypassed.

## DigitalOcean one-go install

The existing production checkout is assumed to be `/opt/vtab-sales-agent`.

```bash
cd /opt/vtab-sales-agent
git fetch origin
git checkout feature/autonomous-web-agent
git pull --ff-only origin feature/autonomous-web-agent
bash deploy/linux/install-autonomous-web-agent.sh
```

The installer will:

- install backend Python dependencies;
- install Playwright Chromium;
- install required Chromium OS libraries where apt permits;
- run Alembic migrations;
- build Next.js;
- install and enable `vtab-sales-web-agent.service`;
- restart existing VTAB Sales services;
- perform basic health checks.

## Verify

```bash
systemctl status vtab-sales-backend --no-pager
systemctl status vtab-sales-frontend --no-pager
systemctl status vtab-sales-worker --no-pager
systemctl status vtab-sales-web-agent --no-pager
journalctl -u vtab-sales-web-agent -n 100 --no-pager
```

Open:

`https://sales.vtabsquare.com/web-agent`

## Configure a source

Use the authenticated API endpoint `POST /api/web-agent/sources` with:

```json
{
  "name": "Example Procurement Portal",
  "url": "https://public.example.org/procurement",
  "country": "Global",
  "category": "Government Procurement",
  "auth_required": false,
  "scan_frequency_minutes": 360,
  "priority": 80
}
```

The worker scans enabled due sources automatically. The Command Center also provides Run Now for configured sources.

## Safety / governance

- Only public HTTP/HTTPS targets are allowed.
- Localhost/private local hostnames and non-web schemes are blocked.
- CAPTCHA, MFA and interactive verification are escalated to human review.
- The browser performs conservative same-host traversal, not uncontrolled crawling.
- Browser findings are treated as evidence candidates, then passed through the existing qualification/research pipeline.
- Contacts are never invented; existing research code uses published evidence and leaves uncertain recipients unverified.
- EOI generation does not imply permission to send.
- Existing production outbound protections remain in force: suppression checks, recipient verification, quota enforcement, approval, and content-bound review.

## Recommended production sizing

Playwright Chromium materially increases memory usage. On a 1 GB droplet, keep one browser worker and scan sources serially. Configure swap and monitor memory. For sustained multi-site concurrency, upgrade the droplet rather than running multiple Chromium workers.

## Rollback

```bash
cd /opt/vtab-sales-agent
git checkout main
git pull --ff-only origin main
systemctl disable --now vtab-sales-web-agent || true
rm -f /etc/systemd/system/vtab-sales-web-agent.service
systemctl daemon-reload
systemctl restart vtab-sales-backend vtab-sales-frontend vtab-sales-worker
```

Database migration rollback is intentionally not automated in the production rollback command, because dropping agent audit/source tables destroys data. If a schema downgrade is explicitly required, back up Neon/PostgreSQL first and then run the relevant Alembic downgrade manually.
