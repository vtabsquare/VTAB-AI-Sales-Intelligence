> Historical source-package notes. Superseded by VALIDATION-REPORT.md. Historical verification labels are not current acceptance results.

# Implementation Manifest

New operating pages:
- `/discovery` — Global Discovery Command Center
- `/portfolio` — VTAB Portfolio Studio
- `/resources` — Resource & Demo Library (company website, Drive/OneDrive, decks, demos, case studies)
- `/templates` — Email Template Studio
- `/schedulers` — Scheduler & Workflow Automation
- `/workflow` — end-to-end workflow and shortcuts

New backend APIs are under `/api/platform/*`.

The previous hard-coded demo opportunity generator is no longer used by `POST /api/opportunities/discover`. Live discovery uses configured sources and never fabricates results when a connector is unavailable.
