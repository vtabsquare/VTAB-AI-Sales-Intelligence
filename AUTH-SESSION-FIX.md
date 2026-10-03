> Historical source-package notes. Superseded by VALIDATION-REPORT.md. Historical verification labels are not current acceptance results.

# VTAB authentication/session fix

Fixed the post-OTP redirect loop.

## Root cause
The application had two different cookie names in use. The login page created `vtab_auth_token`, while Next.js middleware protected the application using only `vtab_session`. The proxy was intended to set `vtab_session`, but the login flow did not confirm that the server-side session cookie was established before redirecting.

## Changes
- `frontend/middleware.ts`: canonical `vtab_session` plus compatibility fallback.
- `frontend/app/backend-api/[...path]/route.ts`: sets both auth cookies on successful OTP verification, forwards either cookie to FastAPI, clears both on logout.
- `frontend/app/login/page.tsx`: after OTP success, validates `/auth/session` before opening `/`.
- `frontend/components/AppSidebar.tsx`: logout clears server cookies and legacy localStorage keys.

No Microsoft Graph credentials, OTP logic, database model, or application data were changed.
