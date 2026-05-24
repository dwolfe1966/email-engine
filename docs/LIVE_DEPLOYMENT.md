# Live Deployment

## Backend API

- Platform: Vercel
- Project: `email-engine-api`
- Production alias: `https://email-engine.app`
- Latest verified deployment: `https://email-engine-bri8icizk-dwolfe1966s-projects.vercel.app`
- Inspect URL: `https://vercel.com/dwolfe1966s-projects/email-engine-api/HAKJZy8Rj7cfmJwfe6mKBraBQBiK`

## SentientMail GUI

- Platform: Vercel
- Project: `ui`
- Production alias: `https://ui-eight-rho.vercel.app`
- Latest verified deployment: `https://ui-qwih5czt6-dwolfe1966s-projects.vercel.app`
- Inspect URL: `https://vercel.com/dwolfe1966s-projects/ui/At4FRENDb8T4FTVBR8qTcHG4Qbj8`

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

Production campaign workflow smoke test:

```bash
CONTACT_EMAIL=<recipient@example.com> scripts/production_campaign_smoke.py
```

The campaign workflow smoke test creates a template, contact, audience, and campaign in the
configured environment, sends one actual campaign test email, records synthetic open/click events,
and verifies campaign analytics. It defaults to `https://email-engine.app`; set
`BASE_URL=http://localhost:8000` for local testing.

SentientMail GUI smoke test:

- `POST /api/render` through `https://ui-eight-rho.vercel.app`
- `POST /api/contacts` through the GUI proxy
- `POST /api/templates` through the GUI proxy
- `POST /api/segments` through the GUI proxy
- `POST /api/sends` through the GUI proxy
- `POST /api/sends/{send_id}/launch` with `dry_run: true`

Live GUI test-mode campaign verification:

- Recipient: `dwolfe66@gmail.com`
- Send ID: `5223ee74-9545-4d49-a725-8f669acc4144`
- Send record ID: `3b8077bd-6a81-477c-a1c5-ce18dd80cb39`
- Requested count: `1`
- Queued count: `1`
- Delivery result: `sent_count=1`, `failed_count=0`
- Tracking result: open and click events recorded through generated tracking URLs.

## Next Deployment Tasks

- Replace `CORS_ORIGINS=["*"]` with the deployed GUI origin once the admin UI URL is final.
- Add app-level authentication before exposing the API beyond private testing.
- Restrict `CORS_ORIGINS=["*"]` after the deployed admin GUI origin is final.
