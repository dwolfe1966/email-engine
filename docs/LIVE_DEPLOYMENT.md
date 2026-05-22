# Live Deployment

## Backend API

- Platform: Vercel
- Project: `email-engine-api`
- Production alias: `https://email-engine.app`
- Latest verified deployment: `https://email-engine-phc2syjxy-dwolfe1966s-projects.vercel.app`
- Inspect URL: `https://vercel.com/dwolfe1966s-projects/email-engine-api/4iry1tMU2FWKWdmD9QyV5TufyBwi`

## Database

- Platform: Neon through Vercel Marketplace
- Resource name: `email-engine-db`
- Resource status at provisioning: `ready`
- External resource ID: `muddy-resonance-28099615`
- Region metadata used: `pdx1`

## Runtime Notes

- Vercel FastAPI entrypoint: `api/index.py`
- Production app path rewrite: all paths route to `/api/index.py`
- Neon migrations were run with `DATABASE_URL_UNPOOLED` from `.env.local`.
- The application normalizes Neon/Vercel `postgresql://` and `postgres://` URLs to SQLAlchemy's `postgresql+psycopg://` driver URL.
- Production email provider: SendGrid.
- The API tester at `/tester` can send an actual provider-backed email to a contact using an existing template and JSON variables.

## Verification

Live smoke test:

```bash
BASE_URL=https://email-engine.app CONTACT_EMAIL=<recipient@example.com> scripts/smoke_test.sh
```

Result:

```text
Smoke test passed.
```

The smoke test verified:

- `GET /health`
- `GET /ready`
- `POST /api/v1/templates`
- `POST /api/v1/audiences/contacts`
- `POST /api/v1/audiences/contacts/{contact_id}/unsubscribe-token`
- `POST /api/v1/emails/send`
- `POST /api/v1/tests/send-email`

## Next Deployment Tasks

- Replace `CORS_ORIGINS=["*"]` with the deployed GUI origin once the admin UI URL is final.
- Add app-level authentication before exposing the API beyond private testing.
- Restrict `CORS_ORIGINS=["*"]` after the deployed admin GUI origin is final.
