> Historical source-package notes. Superseded by VALIDATION-REPORT.md. Historical verification labels are not current acceptance results.

# VTAB AI Sales Intelligence — Final Implementation Candidate

## Implemented workflow
Discovery -> qualification -> company/contact research -> outreach draft -> human approval -> recipient resolution -> email verification -> final human send confirmation -> Microsoft Graph send -> inbox reply sync -> response classification -> follow-up task -> pipeline/dashboard -> agent audit logs.

## Advanced UI included
- Premium sidebar/navigation
- Global Opportunity Dashboard + governed 7-stage journey
- Opportunities
- Approval Queue
- Send Center with recipient verification and send controls
- Response Center
- Pipeline
- AI Agent Logs / observability timeline
- Admin & Microsoft integration control center

## Human-control safeguards
- Approval is separate from send.
- Recipient email is required.
- Recipient verification is required.
- Do-not-contact blocks send.
- Final send confirmation is required.
- `DEMO_MODE=true` simulates delivery.
- `TEST_VERIFIED` is intended for local/development testing only.

## External connections still requiring account-owner action
Microsoft 365 / Outlook requires Entra tenant configuration and admin consent. See `MICROSOFT-OUTLOOK-CONNECTION.md`.

Public opportunity discovery providers/search sources are pluggable. Any provider requiring an account/API credential must be configured with the provider's permitted API and terms before production automation.
