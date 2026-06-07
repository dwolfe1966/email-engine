# Major Platform Gaps

This document tracks the major platform functions that are still missing or immature. It is separate from UI polish work so the project does not mistake a better admin experience for a complete ESP platform.

## Why This Matters

Recent work has improved the native ESP admin UX across templates, audiences, campaigns, and analytics. That polish is useful because it exposes workflow gaps and makes the product easier to reason about. It does not replace the deeper infrastructure required for Email Engine to operate as a production ESP.

Near-term planning should keep two tracks visible:

- **Admin-v2 product polish:** workflow clarity, operator guidance, reporting, previews, and AI-assisted actions.
- **Platform foundations:** data integration, canonical entities, send infrastructure, SMTP, queues, deliverability, governance, and always-on AI agents.

## 1. Data Integration Layer

Current data-source support is early-stage. A production ESP needs a real connector layer that can ingest, map, validate, refresh, and monitor customer data from many systems.

Missing or immature capabilities:

- Connectors for Postgres, MySQL, SQL Server, Snowflake, BigQuery, S3/CSV, REST APIs, Shopify, Stripe, Segment, customer CRMs, and other SaaS systems.
- Schema discovery and schema refresh.
- Multi-table joins between source entities.
- Entity mapping from external schemas into Email Engine canonical objects.
- Client-specific/custom entities without polluting the core schema.
- Incremental sync, scheduled sync, CDC-style ingestion, and webhook/event ingestion.
- Mapping versioning, dry runs, validation reports, replay, and failed-row repair.
- Source health monitoring, sync history, row counts, drift detection, and alerting.

## 2. Canonical Data Model

The platform needs a durable internal data model beyond simple contacts. Data connectors and audience rules should map into stable objects instead of leaking source-specific schemas throughout the product.

Missing or immature capabilities:

- Contact, profile, account, organization, order, product, event, subscription, consent, and custom-object models.
- Identity resolution and merge rules.
- Profile and account relationships.
- Contact-to-event and contact-to-order relationships.
- Consent and subscription state as first-class records.
- Attribute history and event history.
- Client-specific entity definitions and fields.
- Data retention and deletion policies.

## 3. Audience Engine

The current audience builder is useful but still basic. A mature audience engine should support dynamic segmentation across entities, events, attributes, and time windows.

Missing or immature capabilities:

- Nested boolean rule builder in both API and UI.
- Joins across contacts, accounts, events, orders, products, and custom entities.
- Relative time-window rules such as “purchased in last 30 days” or “opened but did not click.”
- Materialized audience snapshots used by campaign launches.
- Incremental audience refresh and preview caching.
- Audience performance history.
- Rule explainability: why a contact matched or did not match.
- Audience overlap, exclusion, and deduplication tools.

## 4. Send Engine

The send engine is one of the largest missing platform areas. Email Engine needs a true queue-driven delivery core.

Missing or immature capabilities:

- Durable send queues.
- Campaign send-job scheduler.
- Per-provider, per-domain, per-account, and per-campaign throttling.
- Retry policy and backoff.
- Dead-letter queues.
- Bounce, complaint, unsubscribe, and suppression processing queues.
- Delivery status transitions with idempotent updates.
- Backpressure controls and operator pause/resume actions.
- Launch-time audience snapshots and immutable send manifests.
- Operational dashboards for queue depth, retry rate, failures, provider errors, and throughput.

## 5. Owned SMTP Server And Provider Layer

Email Engine should not only integrate with external providers. The platform direction is to operate and deeply integrate its own SMTP server capability where needed, while still supporting external providers through adapters.

Target direction:

- Build and manage Email Engine’s own SMTP server infrastructure as a first-class platform component.
- Integrate SMTP acceptance, routing, queueing, retry, bounce handling, and deliverability feedback deeply into the product data model.
- Use third-party providers such as SendGrid, SES, Mailgun, or Postmark as optional delivery adapters, not as the only delivery architecture.

Missing or immature capabilities:

- SMTP server design for outbound delivery control.
- SMTP client support for external relays.
- Provider adapter abstraction.
- Dedicated domain and IP configuration.
- DKIM, SPF, DMARC, BIMI, and bounce-domain management.
- Bounce classification and feedback-loop ingestion.
- Provider webhook ingestion and normalization.
- Deliverability telemetry by domain, provider, IP, campaign, and audience.
- Reputation monitoring and rate-limit decisions.
- Admin controls for throttling, warmup, pausing, and provider failover.

## 6. Tracking And Event Pipeline

Tracking exists in early form, but a production ESP needs a durable event pipeline that can support analytics, automation, AI, and external integrations.

Missing or immature capabilities:

- Durable event ingestion.
- Idempotency and deduplication.
- Event replay.
- Link tracking attribution.
- Bot/open filtering.
- Event aggregation pipelines.
- Export/webhook delivery for customer systems.
- Timeline views per contact, campaign, audience, journey, provider, and domain.
- Event schemas that work across first-party SMTP and third-party providers.

## 7. AI As An Operating Layer

AI is currently mostly endpoint- and button-driven. The longer-term UX should treat AI as an always-present operating layer that understands context and can propose or execute approved actions.

Missing or immature capabilities:

- Always-present workflow assistant across major product areas.
- Context-aware agents on templates, campaigns, audiences, data sources, delivery, analytics, journeys, and account settings.
- Agent memory of current workflow state and historical decisions.
- Background monitoring agents for deliverability, data quality, audience drift, campaign readiness, and import failures.
- Guardrails, approvals, permissions, and audit trails for AI-suggested actions.
- AI recommendations tied directly to product actions.
- Human-in-the-loop review for launches, data mutations, suppression changes, provider changes, and account/security changes.

## 8. Security, Multi-Tenant, And Governance

The product needs deeper account and governance infrastructure before it can support production customers safely.

Missing or immature capabilities:

- Accounts/workspaces.
- Roles and permissions.
- API keys, scopes, and credential management.
- Credential vaulting.
- Activity logs and audit logs.
- Request IDs and structured logs.
- Data access controls per account/client.
- Provider-configuration permissions.
- Data export permissions.
- Admin mutation review and incident investigation surfaces.

## Recommended Platform Foundation Sequence

The highest-value deeper engineering sequence is:

1. Canonical data/entity model.
2. Data connector architecture.
3. Send engine architecture.
4. Owned SMTP server and provider adapter architecture.
5. Tracking/event pipeline hardening.
6. Activity and audit logging.
7. Account, permissions, credentials, and API-key management.
8. AI agent architecture and governance.

UX polish should continue where it exposes real workflow gaps, but platform foundation work should become a parallel track and should drive the next major architecture decisions.
