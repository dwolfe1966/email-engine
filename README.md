# Email Platform Python

A production-oriented Python scaffold for a lifecycle/email platform. It supports campaign and template management, audience ingestion, event tracking, unsubscribe/compliance endpoints, and provider-backed email sending.

## Stack

- **FastAPI** for API service
- **SQLAlchemy 2.x + Alembic** for persistence/migrations
- **PostgreSQL** for data storage
- **Pydantic Settings** for configuration
- **SendGrid or SMTP** provider abstraction
- **Pytest** for tests
- **Ruff + MyPy** for code quality
- **Docker Compose** for local development
- **Docker** for deployable application images

## Quick start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d postgres
alembic upgrade head
uvicorn email_platform.main:app --reload
```

Open: `http://localhost:8000/docs`

Docker local run:

```bash
docker compose up --build
```

Run migrations against the Compose database:

```bash
DATABASE_URL=postgresql+psycopg://email_platform:email_platform@localhost:5432/email_platform alembic upgrade head
```

## Local test

```bash
pytest
ruff check .
mypy src
```

## Deployment

See `docs/DEPLOYMENT.md`. The repository includes a `Dockerfile`; run `alembic upgrade head` against the production database before starting the web process.

## Repository layout

```text
src/email_platform/
  api/              FastAPI routers
  core/             settings, security, logging
  db/               SQLAlchemy session/base
  models/           ORM models
  schemas/          API contracts
  services/         business logic
  providers/        email delivery providers
  workers/          background jobs placeholder
alembic/            database migrations
tests/              unit/API tests
```

## Initial API surface

- `GET /health`
- `GET /api/v1/templates`
- `POST /api/v1/templates`
- `GET /api/v1/templates/{template_id}`
- `GET /api/v1/campaigns`
- `POST /api/v1/campaigns`
- `GET /api/v1/campaigns/{campaign_id}`
- `GET /api/v1/audiences/contacts`
- `POST /api/v1/audiences/contacts`
- `GET /api/v1/audiences/contacts/{contact_id}`
- `POST /api/v1/audiences/contacts/{contact_id}/unsubscribe-token`
- `POST /api/v1/send/contact`
- `POST /api/v1/send/test`
- `GET /api/v1/events`
- `POST /api/v1/events`
- `GET /api/v1/events/{event_id}`
- `GET /api/v1/unsubscribe/{token}`

See `docs/API_INTEGRATION.md` for GUI integration details.

## Notes

This is intentionally provider-neutral. Start with `EMAIL_PROVIDER=console` for local development, then switch to `sendgrid` or `smtp`.
