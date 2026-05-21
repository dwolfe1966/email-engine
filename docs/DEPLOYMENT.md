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

The repository includes `render.yaml` for a Docker web service plus managed Postgres. It uses Render's `preDeployCommand` to run `alembic upgrade head` before the service starts.

1. Create a new Render Blueprint from this repository.
2. Set `CORS_ORIGINS` to the GUI origin, for example `["https://admin.example.com"]`.
3. Set `DEFAULT_FROM_EMAIL` to a verified sender.
4. Leave `EMAIL_PROVIDER=console` for the first deploy.
5. Render runs migrations through `preDeployCommand: alembic upgrade head`.

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
