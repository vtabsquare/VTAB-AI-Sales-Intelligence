# Phase 1 implementation design

Extend the existing Next.js/FastAPI platform rather than replacing its reviewed send controls.
Frontend requests pass through the same-origin proxy and database-backed session authentication.
FastAPI coordinates specialized discovery, qualification, evidence research, capability matching and outreach tools. A persisted workflow checkpoints each completed step; retry resumes at the failed step. Only the existing human approval/send route can deliver email.

## Repository
- frontend/app: operations pages, knowledge workspace, opportunity detail and scoring
- backend/app/agents: structured provider, qualification and supervisor
- backend/app/prompts: versioned agent instructions
- backend/app/models/intelligence.py: scores, source occurrences, workflow state, knowledge chunks
- backend/alembic: explicit migrations
- backend/app/worker.py: separate scheduler process
- docs: architecture, security, database, local setup and validation

## ER model
Company 1 → many Opportunities and Contacts. Opportunity 1 → many DiscoveryOccurrences, OutreachDrafts and AgentRuns (run input contains opportunity ID). Opportunity 1 → 1 QualificationAssessment and IntelligenceWorkflow. KnowledgeDocument 1 → many KnowledgeChunks. Existing Communications, Suppressions, FollowUps and Sessions remain in use.

## Services and configuration
DATABASE_URL, JWT_SECRET, LOGIN_EMAIL, LOGIN_PASSWORD, DEMO_MODE, DEMO_AUTH, AI_PROVIDER, OPENAI_API_KEY, OPENAI_MODEL and provider endpoints configure the application. Graph credentials and SERPER_API_KEY are optional external integrations. Demo auth is an explicit development-only OTP mode and never calls Graph.

## Assumptions and controls

## Deployment correction
Windows-native Python + Next.js + the existing SQL Server is the required deployment path. Docker/PostgreSQL execution is not required. Follow README.md and local-development.md. Live Microsoft 365 and SQL Server acceptance remain pending.
