# Product Backlog

This backlog is organized around the target platform capabilities:

1. Mapping and pulling from complex heterogeneous data stores
2. Audience building
3. Campaign management
4. Template development with robust dynamic-template language
5. Journey management
6. Delivery management with work queues
7. Tracking
8. Analytics

## P0: Platform Foundation

- Add production authentication for GUI-to-API requests.
- Add list response envelopes with `items`, `limit`, `offset`, and `total`.
- Add update/delete endpoints for templates, campaigns, contacts, data sources, and audiences.
- Add audit logs for admin mutations.
- Add structured JSON logging and request IDs.
- Add release-phase migration automation for the deployment platform.

## P1: Data Source Mapping And Ingestion

- Add `data_sources` for Postgres, MySQL, Snowflake, BigQuery, REST APIs, CSV/S3, and manual uploads.
- Add `data_source_mappings` to map external fields into canonical contact/profile/event objects.
- Add connection validation endpoints that do not expose credentials.
- Add schema discovery endpoints for tables, columns, and sample rows.
- Add ingestion jobs with status, counts, errors, and retry metadata.
- Add normalized profile/contact attribute merge rules.
- Add read-only connector execution with allowlisted queries or parameterized extraction plans.

## P2: Audience Building

- Add `audiences` with rule-tree definitions over contact fields, attributes, events, and imported data.
- Add audience preview endpoints with estimated counts and sample contacts.
- Add materialized audience membership snapshots for repeatable campaign sends.
- Add exclusion logic for unsubscribed, suppressed, bounced, complained, and manually excluded contacts.
- Add audience versioning so a campaign can reference the exact audience definition used at send time.

## P3: Campaign Management

- Add campaign update/delete endpoints and status transitions.
- Add campaign scheduling fields and launch endpoint.
- Add campaign approval gates and validation checks.
- Add campaign send summary fields: queued, sent, delivered, opened, clicked, bounced, complained, unsubscribed, failed.
- Add campaign cloning and draft/version workflow.

## P4: Template Development

- Add template preview and validation endpoints. **Initial sandboxed preview/validation shipped.**
- Add template variable extraction and required-variable contracts. **Initial undeclared/missing variable extraction shipped.**
- Add template versions with immutable snapshots.
- Add reusable partials/components.
- Add support for robust Jinja2 features with a sandboxed environment. **Initial sandboxed renderer shipped.**
- Add template linting for unsubscribe links, tracking links, missing variables, and unsafe content.
- Add approval workflow for production templates.

## P5: Journey Management

- Add `journeys`, `journey_steps`, and `journey_enrollments`.
- Add trigger types: event, audience entry, schedule, API call, and manual enrollment.
- Add delay/wait steps and conditional branches.
- Add suppression and exit rules.
- Add journey run history and per-contact timeline.

## P6: Delivery Management And Work Queues

- Add durable `email_send_records` separate from provider events. **Initial foundation shipped.**
- Add campaign fanout jobs and per-recipient send jobs. **Initial foundation shipped.**
- Add queue backend abstraction, starting with database-backed queues and moving to SQS/RabbitMQ.
- Add worker process for batch rendering and sending. **Initial on-demand processor shipped.**
- Add retry/backoff handling for transient delivery errors.
- Add domain throttling rules and per-provider rate controls.
- Add suppression checks before send.
- Keep provider interfaces neutral so SendGrid, SMTP/Postfix, Mailgun, and future providers can be swapped without changing campaign, audience, template, tracking, or analytics domains.

## P7: Tracking And Provider Webhooks

- Add SendGrid webhook endpoint with signature verification. **Verifier support shipped; production enforcement requires configuring the SendGrid public key.**
- Add suppression updates for hard bounces, spam complaints, and unsubscribes. **Initial suppression handling shipped.**
- Add provider-neutral webhook/event adapters so SendGrid-specific logic does not leak into the core event, suppression, or analytics models.
- Add open pixel endpoint with signed tracking IDs.
- Add click redirect endpoint with signed tracking IDs.
- Add provider message ID correlation to send records.
- Add event timeline endpoints for contacts, campaigns, and journeys.
  **Initial filterable email event timeline endpoints shipped.**

## P8: Analytics

- Add campaign rollups for sent, delivered, opened, clicked, bounced, complained, unsubscribed, failed, and suppressed counts.
  **Initial campaign performance report endpoint shipped.**
- Add dashboard summary endpoint for the GUI.
  **Initial v1 analytics overview endpoint shipped.**
- Add audience performance reports.
- Add journey performance reports by step and branch.
  **Initial journey and step performance report endpoint shipped.**
- Add provider/domain deliverability reports.
  **Initial domain deliverability report endpoint shipped.**
- Add cohort reports by source, segment, and imported data attributes.

## P9: Scale, Operations, And Compliance

- Add staging environment and deployment promotion gates.
- Add dependency/security scanning.
- Add load tests for ingestion, audience preview, campaign fanout, and provider delivery.
- Add OpenTelemetry tracing and metrics.
- Add privacy export/delete workflows.
- Add Terraform/Pulumi for production infrastructure once worker/queue needs outgrow Vercel.
