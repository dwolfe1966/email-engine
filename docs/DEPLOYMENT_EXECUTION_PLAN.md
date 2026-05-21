# Deployment Execution Plan

## Target Assumption

Default target is a Docker web service backed by managed PostgreSQL. The checked-in `render.yaml` gives a concrete Render path, but the same image can run on Fly.io, Railway, ECS, Cloud Run, or a VM.

## Phase 1: Repository Readiness

- Container image builds from `Dockerfile`.
- Runtime ignores local/dev files through `.dockerignore`.
- `GET /health` checks process liveness.
- `GET /ready` checks database connectivity.
- CI provisions Postgres and runs Alembic migrations.
- Smoke test script exercises the first production workflow.

## Phase 2: First Deployment

1. Provision managed Postgres.
2. Configure environment:
   - `ENVIRONMENT=production`
   - `DATABASE_URL=<managed postgres url>`
   - `CORS_ORIGINS=["<deployed GUI origin>"]`
   - `EMAIL_PROVIDER=console`
   - `DEFAULT_FROM_EMAIL=<verified sender>`
   - `UNSUBSCRIBE_SECRET=<stable random secret>`
3. Build and deploy the Docker image.
4. Run `alembic upgrade head`.
5. Verify `/health`, `/ready`, and `/docs`.
6. Run `BASE_URL=<api url> scripts/smoke_test.sh`.

## Phase 3: Email Provider Activation

1. Configure either SendGrid or SMTP.
2. Keep `EMAIL_PROVIDER=console` until smoke tests pass.
3. Switch `EMAIL_PROVIDER=sendgrid` or `smtp`.
4. Send a controlled test message.
5. Add provider webhook handling before using production campaigns.

## Phase 4: GUI Integration

1. Add an API compatibility layer or update the SentientMail GUI API client.
2. Prioritize templates, contacts, sends/campaigns, and reports.
3. Add authentication before exposing mutation endpoints to the GUI.
4. Add provider webhook endpoints and event rollups.

## Live Deployment Blockers

- Hosting target and credentials are not available in this workspace.
- Production `DATABASE_URL`, `CORS_ORIGINS`, `DEFAULT_FROM_EMAIL`, and provider secrets are not available.
- Local shell currently lacks Python 3.11 and project dev tools, so local Python checks require environment setup or CI.
