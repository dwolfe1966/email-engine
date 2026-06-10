# Deployment

This service is a FastAPI application backed by PostgreSQL. It can run anywhere that supports Python 3.11 and a Postgres connection string. The included `Dockerfile` is the safest default for Render, Fly.io, Railway, ECS, Cloud Run, or a VM.

## Execution Plan

1. Build and test the application image.
2. Provision managed PostgreSQL.
3. Configure production environment variables.
4. Run `alembic upgrade head` against the production database.
5. Start the web service.
6. Run the smoke test against the deployed URL.
7. Switch `EMAIL_PROVIDER` from `console` to `sendgrid` or `smtp` only after the API smoke test passes.

## Required Runtime

- Python 3.11
- PostgreSQL 16 or compatible managed Postgres
- Environment variables from `.env.example`
- Alembic migrations applied before serving traffic

## Environment

Required:

- `DATABASE_URL`: SQLAlchemy URL, for example `postgresql+psycopg://user:password@host:5432/dbname`
- `DATABASE_MIGRATION_URL`: optional direct database URL for Alembic migrations. Use this for Neon direct/unpooled connections.
- `UNSUBSCRIBE_SECRET`: long random secret used to sign unsubscribe links
- `DEFAULT_FROM_EMAIL`: verified sender address
- `EMAIL_PROVIDER`: `console`, `sendgrid`, or `smtp`
- `CORS_ORIGINS`: JSON list of allowed GUI origins, for example `["https://app.example.com"]`

Provider-specific:

- SendGrid: `SENDGRID_API_KEY`
- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`
- Managed SMTP feedback: `MANAGED_SMTP_FEEDBACK_SECRET`

## Deploy With Docker

Build:

```bash
docker build -t email-platform .
```

Run:

```bash
docker run --rm -p 8000:8000 --env-file .env email-platform
```

Run migrations before first traffic and on every schema change:

```bash
alembic upgrade head
```

On platforms with one-off jobs, run the migration command as a release phase or deploy hook before starting the web process.

## Deploy With Render Blueprint

The repository includes `render.yaml` for a Docker web service, managed Postgres, and two managed
SMTP cron jobs. It uses Render's `preDeployCommand` to run `alembic upgrade head` before the web
service starts.

1. Create a new Render Blueprint from this repository.
2. Set `CORS_ORIGINS` to the GUI origin, for example `["https://admin.example.com"]`.
3. Set `DEFAULT_FROM_EMAIL` to a verified sender.
4. Leave `EMAIL_PROVIDER=console` for the first deploy.
5. Render runs migrations through `preDeployCommand: alembic upgrade head`.
6. Set `BASE_URL` on both managed-SMTP cron jobs to the deployed API origin.
7. Set matching `MANAGED_SMTP_FEEDBACK_SECRET` values on the web service and DSN ingestion cron
   before enabling bounce-domain ingestion.
8. Set `MANAGED_SMTP_DSN_PATH`, `MANAGED_SMTP_DSN_ARCHIVE`, and
   `MANAGED_SMTP_DSN_QUARANTINE` on
   `email-engine-managed-smtp-dsn-ingestion` when a production Maildir is mounted or otherwise
   available to the job.
9. Set `EMAIL_ENGINE_COOKIE` on `email-engine-managed-smtp-maintenance` if the deployed API requires
   an authenticated operator session for scheduled maintenance.

## Deploy With Vercel + Neon

Vercel can host the FastAPI app through the Python runtime using root `app.py`. Neon provides Postgres.

1. Create a Neon project.
2. Set Vercel environment variables:
   - `DATABASE_URL`: Neon pooled or direct SQLAlchemy URL
   - `DATABASE_MIGRATION_URL`: Neon direct SQLAlchemy URL
   - `ENVIRONMENT=production`
   - `CORS_ORIGINS=["https://your-gui.vercel.app"]`
   - `EMAIL_PROVIDER=console`
   - `DEFAULT_FROM_EMAIL=<verified sender>`
   - `UNSUBSCRIBE_SECRET=<stable random secret>`
3. Run migrations from a trusted CLI/CI environment:

```bash
PYTHONPATH=src DATABASE_MIGRATION_URL=<neon-direct-url> alembic upgrade head
```

4. Deploy:

```bash
vercel deploy --prod
```

Use Docker hosting instead if you need long-running workers, queue consumers, or provider webhook processing with strict runtime control.

## Managed SMTP Staging

The first owned-MTA staging path uses Postfix as a constrained outbound transport while Email
Engine keeps queue state, route policy, feedback ingestion, suppressions, and analytics.

Staging files live in `infra/managed-smtp/`:

```bash
docker compose -f infra/managed-smtp/docker-compose.staging.yml up --build -d
```

For Email Engine submission against the staging MTA:

```text
EMAIL_PROVIDER=smtp
SMTP_HOST=<mta-host>
SMTP_PORT=2587
SMTP_USE_TLS=false
MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret>
```

The MTA or feedback worker should post signed feedback to
`/api/v1/delivery/managed-smtp/feedback`. See `infra/managed-smtp/README.md` and
`scripts/managed_smtp_feedback_smoke.py`.

Before production sends, run the controlled delivery script against a staging domain policy and a
seed campaign:

```bash
DOMAIN_POLICY_ID=<domain-policy-id> \
CAMPAIGN_ID=<campaign-id> \
SEED_EMAIL=seed@example.com \
MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret> \
BASE_URL=https://<email-engine-api> \
python scripts/managed_smtp_controlled_delivery.py --send-seed --post-feedback
```

It verifies diagnostics, DNS authentication, reputation/compliance readiness, optional seed delivery,
and signed managed-SMTP feedback ingestion in one operator runbook.

For staging MTA log forwarding, normalize Postfix delivery lines into signed feedback events:

```bash
tail -F /var/log/mail.log \
  | MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret> \
    BASE_URL=https://<email-engine-api> \
    python scripts/managed_smtp_log_feedback.py --post -
```

For bounce-domain DSN mailbox forwarding, normalize RFC822 DSN messages into the same feedback
path:

```bash
MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret> \
BASE_URL=https://<email-engine-api> \
python scripts/managed_smtp_dsn_feedback.py --post --archive-maildir /path/to/archive-Maildir /path/to/Maildir
```

For scheduled maintenance, use the combined runbook from cron or your scheduler. It runs the
managed-SMTP maintenance endpoint and, when `MANAGED_SMTP_DSN_PATH` is set, ingests DSN mailbox
feedback in the same run:

```bash
BASE_URL=https://<email-engine-api> \
EMAIL_ENGINE_COOKIE='<operator session cookie if auth is required>' \
MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret> \
MANAGED_SMTP_DSN_PATH=/path/to/Maildir \
MANAGED_SMTP_DSN_ARCHIVE=/path/to/archive-Maildir \
MANAGED_SMTP_DSN_QUARANTINE=/path/to/quarantine-Maildir \
python scripts/managed_smtp_maintenance_runbook.py
```

On Render, `render.yaml` splits that runbook into two production cron jobs:

- `email-engine-managed-smtp-dsn-ingestion`: every 10 minutes, runs
  `python scripts/managed_smtp_maintenance_runbook.py --skip-maintenance`.
- `email-engine-managed-smtp-maintenance`: daily at 06:17 UTC, runs
  `python scripts/managed_smtp_maintenance_runbook.py --skip-dsn`.

This keeps DSN acknowledgement responsive without running DNSBL scans and warmup progression on
every mailbox poll.

When `MANAGED_SMTP_DSN_QUARANTINE` is set, malformed or non-DSN mailbox messages are moved to that
Maildir instead of being replayed on every scheduler run. Successfully parsed messages are still
archived only after their feedback post succeeds.

## Health Check

Use:

```text
GET /health
```

Readiness, including database connectivity:

```text
GET /ready
```

Expected response:

```json
{"status":"ok","environment":"production"}
```

## Production Checklist

- Set `ENVIRONMENT=production`.
- Set `CORS_ORIGINS` to the deployed GUI origin, not `["*"]`.
- Set `UNSUBSCRIBE_SECRET` to a strong secret and keep it stable across deployments.
- Use managed Postgres and run `alembic upgrade head`.
- Start with `EMAIL_PROVIDER=console` for smoke tests, then switch to `sendgrid` or `smtp`.
- Verify `/docs` loads and `/health` returns `ok`.
- Verify `/ready` returns `ready`.
- Create a template, create/upsert a contact, generate an unsubscribe token, and send a console test email before enabling real provider sending.

## Smoke Test

After migrations and web startup:

```bash
BASE_URL=https://your-api.example.com scripts/smoke_test.sh
```

The smoke test checks health/readiness, creates a template, upserts a contact, generates an unsubscribe token, and sends one console-provider test email.
