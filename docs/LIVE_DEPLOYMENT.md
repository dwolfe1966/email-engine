# Live Deployment

## Backend API

- Platform: Vercel
- Project: `email-engine-api`
- Production alias: `https://email-engine.app`
- Latest verified deployment: `https://email-engine-4j7bzn3yl-dwolfe1966s-projects.vercel.app`
- Inspect URL: `https://vercel.com/dwolfe1966s-projects/email-engine-api/59GtZLKvyUfrrjZYLPmVPjHNSwPb`

## SentientMail GUI

- Platform: Vercel
- Project: `ui`
- Production alias: `https://ui-eight-rho.vercel.app`
- Latest verified deployment: `https://ui-2u18vlfu8-dwolfe1966s-projects.vercel.app`
- Inspect URL: `https://vercel.com/dwolfe1966s-projects/ui/63caGxZ44jgQh9B8vMsumHXS36Qy`

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

Latest production campaign workflow result, run May 24, 2026:

- Recipient: `dwolfe66@gmail.com`
- Template ID: `8420c67d-5b80-49ca-9e2e-cf094e5d3697`
- Contact ID: `1e406555-0fb4-4712-9758-10167e501015`
- Audience ID: `03b8e226-bf63-492d-8fd7-901c0824e85e`
- Campaign ID: `b6ad7dba-a9de-416c-83d5-6f0e3ee84cb3`
- Send job ID: `9a853e43-3b99-407d-9108-576a8ee5b493`
- Send record ID: `8384c350-95ba-4656-a68a-29fc1c59908e`
- Analytics verified: `sent_count=1`, `opened_count=1`, `clicked_count=1`

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
