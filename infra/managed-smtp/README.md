# Managed SMTP Staging

This scaffold is the first concrete owned-MTA deployment path. It chooses Postfix for staging
because Postfix is mature, operationally familiar, and works well as a constrained outbound
transport while Email Engine owns queue state, feedback normalization, and operator controls.

It is not a production deliverability stack yet. Production still needs DKIM signing, SPF/DMARC
alignment, bounce-domain routing, abuse controls, IP pool policy, warmup automation, queue
observability, and blocklist monitoring.

## Components

- `postfix/`: minimal Postfix container for constrained staging.
- `docker-compose.staging.yml`: standalone MTA compose file with SMTP on host port `2525` and
  submission on host port `2587`.
- `scripts/managed_smtp_feedback_smoke.py`: signs and posts a sample feedback event to Email
  Engine's managed-SMTP feedback endpoint.

## Staging Flow

1. Deploy Email Engine with `MANAGED_SMTP_FEEDBACK_SECRET` configured.
2. Start the staging MTA:

   ```bash
   docker compose -f infra/managed-smtp/docker-compose.staging.yml up --build -d
   ```

3. Configure Email Engine for staging submission:

   ```text
   EMAIL_PROVIDER=smtp
   SMTP_HOST=<mta-host>
   SMTP_PORT=2587
   SMTP_USE_TLS=false
   DEFAULT_FROM_EMAIL=no-reply@<staging-domain>
   ```

4. Send only to a low-volume seed list on a staging domain.
5. Post a signed feedback smoke event:

   ```bash
   MANAGED_SMTP_FEEDBACK_SECRET=<secret> \
   BASE_URL=https://<email-engine-api> \
   python scripts/managed_smtp_feedback_smoke.py
   ```

6. Confirm `/api/v1/analytics/overview`, Delivery Manager, and suppressions reflect the feedback.

## MTA Boundary

Postfix handles SMTP transport. Email Engine remains responsible for:

- send job and recipient queue state
- domain route policy
- retry/dead-letter operator controls
- signed feedback ingestion
- suppression creation
- analytics rollups

The first staging feedback path is API-based. Later slices should add DSN parsing and MTA log
forwarding that emit the same signed `ManagedSmtpFeedbackEvent` payloads.
