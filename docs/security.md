# Security and release controls

Knowledge is unapproved by default; withdrawn evidence immediately disappears from retrieval. Demo fixtures are excluded from live retrieval. Provider models have no email-send tool and cannot bypass deterministic rejection gates. External HTTP source requests reject private/loopback/reserved resolved addresses, credentials and nonstandard ports; redirects are checked again. Response-size and timeout limits apply. Production egress controls are still needed to prevent DNS rebinding and constrain external sources. Only automate sources with permission.

## Deployment correction
Windows-native Python + Next.js + the existing SQL Server is the required deployment path. Docker/PostgreSQL execution is not required. Follow README.md and local-development.md. Live Microsoft 365 and SQL Server acceptance remain pending.
