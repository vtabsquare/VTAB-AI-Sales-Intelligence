# VTAB Square Sales Manager

This release extends the existing application and Neon PostgreSQL schema. It uses native Python/Node runtimes. Docker is not required.

## Owner workflow

1. In **Portfolio Studio**, configure the actual services VTAB offers, keywords and buyers. IT support and cloud service categories are provided as starting entries; they are not verified capability claims.
2. In **Knowledge Base**, add and approve the company introduction, AI adoption initiative, agent capabilities, delivery model and factual collateral summaries. Live qualification and drafting exclude demo knowledge.
3. Configure countries and RSS, website or web-search discovery sources in **Discovery Engine**. Web search requires `SERPER_API_KEY`. Searches rotate through service/country queries in batches of 30. This searches configured public sources; it does not guarantee complete worldwide coverage or access private LinkedIn content.
4. In **Sales Manager**, save the agent policy. Enable automated initial EOI and fixed acknowledgements separately if desired. Recipient source evidence must first be reviewed in Send Center; domain/MX checks alone do not prove a mailbox exists or authorize sending.
5. Create a `SALES_CYCLE` schedule (for example every 15 minutes) and an optional daily `RESOURCE_SYNC` schedule. A cycle discovers, qualifies, researches, prepares initial drafts, syncs the configured inbox, prepares detailed replies and delivers content-specific approved responses. Demo cycles skip real inbox reads and simulate all sends.
6. A matched external reply opens one casebook per organization. It includes earlier recorded outreach, incoming messages, revisions, owner approval and subsequent delivery history. Unmatched mail needs manual investigation; it is never assigned to the latest unrelated lead. System notices do not open client cases.
7. Read the client's request and proposed response in Sales Manager. Supply suggestions for AI revision, or edit the response yourself. **Save edited response**, then **Approve for next cycle**. Approval authorizes delivery of that exact subject/body in the next enabled cycle. Any revision cancels approval. Follow-up-later tasks also respect their due date.
8. Update casebook status through engaged, proposal, negotiation, won/lost/closed and record owner notes. Review execution history in Job Monitor.

## Example

A configured feed publishes a buyer's Power BI/Fabric support RFP. The cycle records the source, evaluates it against approved VTAB facts and extracts published email/`tel:` phone candidates. A recipient with reviewed source evidence can receive the initial EOI when automatic initial outreach is enabled. A reply asking for AI-assisted reporting creates a casebook and a response task. The agent can send a fixed receipt acknowledgement, but the substantive answer waits for your review. You request a Fabric-focused revision, save/review it, approve the new version, and the next cycle sends it through Microsoft Graph. The casebook preserves each decision and message. Missing contacts, unsupported claims and ambiguous recipient matches stay for review.

## Private integration configuration

Configure these in the hosting environment or the protected worker environment file. Never commit credentials.

| Integration | Configuration | Scope and behavior |
|---|---|---|
| Neon | `DATABASE_URL` | Existing PostgreSQL connection; keep certificate verification enabled. |
| Microsoft 365 | `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_SENDER_EMAIL=contactsales@vtabsquare.com` | Tenant administrator grants application Mail.Read and Mail.Send and restricts the application to the required mailbox. Delta inbox import is read-only. Outbound send uses the configured mailbox. |
| AI | `AI_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-5-mini` | Structured draft generation. Without live provider configuration, the UI labels local starter text; local feedback is not represented as an AI revision. Azure requires its deployment endpoint/model configuration. |
| Google Drive | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_DRIVE_FOLDER_IDS` | Obtain owner consent with read-only Drive access. Comma-separated folder IDs scope the importer. Direct children are paginated and catalogued. This release does not extract binary presentation contents or transcribe videos; add reviewed summaries. Imported links are inactive by default and sharing permissions are not changed. |
| Company websites | Add a Company Website source in Sales Manager | Imports the configured public page as unapproved knowledge. Does not crawl the whole website. |
| GitHub | Add exact repository URL in Sales Manager; optional `GITHUB_READ_TOKEN` | Read-only README import. For private repositories, use a fine-grained token restricted to selected repositories with contents read permission. The agent does not execute or modify repository code. |

Imported or changed external knowledge requires owner approval. Reviewed public collateral links can be supplied in manually edited replies; the AI prompt does not automatically share private Drive URLs.

## Reliable periodic execution without Docker

Sleeping/free web processes cannot serve as the always-on scheduler. Run the native worker on an always-on host, such as an existing DigitalOcean machine with confirmed available capacity. Deployment has not been performed by this code change.

1. Install the backend dependencies into `/opt/vtab-sales/backend/.venv` and deploy the same commit used by the API.
2. Set the private environment file `/etc/vtab-sales/backend.env`, readable by the `vtab` service user only. Use the same database and mailbox configuration as the API. Start with `DEMO_MODE=true`.
3. Run `alembic upgrade head` once before starting the new API/worker release. Revision `0004_sales_manager` adds tables and preserves existing records. Back up the production database before rollout.
4. Install the supplied `deploy/vtab-sales-worker.service`, adapting paths/user to your host. Run `systemctl daemon-reload` and `systemctl enable --now vtab-sales-worker`.
5. Keep `SCHEDULER_ENABLED=false` in the web API. The standalone `python -m app.worker` runs a minute tick regardless of that web flag. Sales Manager shows the most recent scheduler heartbeat. Check `systemctl status` and `journalctl -u vtab-sales-worker` for failures.
6. Save schedules, validate a complete demo cycle, then validate Mail.Read and a controlled approved send to an owner-authorized test recipient before changing `DEMO_MODE=false` and enabling real automated outreach.

Database leases prevent overlapping complete sales cycles and renew during long runs. A stopped worker's lease expires after one hour. Failed/ambiguous sends consume the daily attempt quota and are never retried automatically. A response task with a delivery error moves to `DELIVERY_REVIEW`; check Microsoft Sent Items and provider records, then use **Confirm already sent** or **Confirm not sent · review again** in Sales Manager with an evidence note. A new attempt needs a new content-specific approval. Graph acceptance is recorded as `GRAPH_ACCEPTED`, not a delivery/open confirmation. There is no delivery/open telemetry in this release. The daily UTC limit applies to all outbound sends, including acknowledgements and manually confirmed sends.

## Validation and remaining live work

Automated acceptance uses isolated SQLite, simulated outbound delivery and mocked provider contracts. The frontend production build is checked separately. These results do not establish successful access to the actual Microsoft tenant, Google folders, private repository, Neon production database or an always-on host. Those integrations require configured credentials/consent and a controlled live acceptance run. Do not confuse enabling an agent policy with deploying a worker.
