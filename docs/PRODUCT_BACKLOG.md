# Product Backlog

## P0: Deployable MVP

- Add production authentication for GUI-to-API requests.
- Add provider webhook endpoints for SendGrid and SMTP-compatible event ingestion.
- Add campaign send orchestration beyond test sends.
- Add CI Postgres service or test database strategy for DB-backed endpoint tests.
- Add release-phase migration command in the chosen hosting platform.

## P1: GUI Integration

- Add update/delete endpoints for templates, campaigns, and contacts.
- Add campaign status transitions: draft, scheduled, paused, sending, sent.
- Add audience filtering based on contact attributes and unsubscribe status.
- Add list response envelopes with `items`, `limit`, `offset`, and `total`.
- Add validation and preview endpoints for template variables.

## P2: Email Platform Core

- Add background workers for campaign fanout and retry handling.
- Add email send records separate from provider event records.
- Add suppression lists for bounced, complained, and unsubscribed addresses.
- Add template versioning and approval workflow.
- Add click/open tracking with signed redirect and pixel endpoints.

## P3: Operations and Compliance

- Add structured logging, request IDs, and metrics.
- Add rate limits for public endpoints.
- Add audit logs for contact and campaign changes.
- Add data export/delete workflows for privacy requests.
- Add domain authentication setup docs for the selected provider.

## P4: Analytics

- Add campaign rollups for sent, delivered, opened, clicked, bounced, complained, and unsubscribed counts.
- Add event timeline endpoints for contacts and campaigns.
- Add dashboard summary endpoint for the GUI.
- Add cohort/audience performance reporting.
