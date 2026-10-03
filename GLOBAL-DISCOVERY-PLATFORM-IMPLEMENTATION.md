# VTAB AI Sales Intelligence — Global Discovery Platform

## Implemented
- Demo discovery removed from the live discovery route.
- Portfolio-driven query generation and evidence-based matching.
- Live global web search connector (Serper API key required).
- RSS/Atom and configured website connectors that do not require a search API key.
- Source URLs retained on every discovered opportunity; no synthetic opportunity URLs are created.
- Portfolio Studio for adding services, descriptions, keywords and target buyers.
- Discovery Command Center for source configuration, generated search intents and live runs.
- Resource & Demo Library for company sites, Google Drive/OneDrive folders, decks, demos and case studies.
- Email Template Studio with personalization placeholders.
- Scheduler Center for recurring DISCOVERY, INBOX_SYNC and REPROCESS workflows.
- Scheduler deliberately excludes automatic outbound email.
- Existing Microsoft Graph, Response Center, approval and Send Center preserved.

## Live web search configuration
The application does not embed or ship a third-party search credential. Add your own provider key to `backend/.env`:

`SERPER_API_KEY=<your key>`

Without this key, the Global Web Search connector is skipped transparently. Configured RSS and WEBSITE sources still operate live. The UI and Agent Logs report skipped connectors/errors rather than creating demo results.

## Recommended first run
1. Keep the existing working `backend/.env` (Microsoft credentials are not included in this package).
2. Add `SERPER_API_KEY` if you want general web search.
3. Start backend and frontend.
4. Open Portfolio Studio and confirm/add VTAB services.
5. Open Discovery Engine and add procurement RSS feeds / procurement website URLs you are authorized to access.
6. Run Discovery Now.
7. Review Opportunities; every live result includes its source URL and match rationale.
8. Create schedules only after a manual discovery run has been validated.

## Safety
`DEMO_MODE=true` remains recommended while validating the discovery and matching layers. Scheduled workflows can discover/read/reprocess, but cannot send customer email.
