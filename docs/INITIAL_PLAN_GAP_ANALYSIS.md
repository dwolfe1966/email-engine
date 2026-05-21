# Initial Plan Gap Analysis

Source plan: `docs/initial-plan.pdf`

Assessment date: 2026-05-21

## Executive Summary

The current `email-engine` repository implements and deploys a narrow API-first MVP: template
CRUD, campaign CRUD, contact upsert/list/get, manual event ingestion, unsubscribe token handling,
provider-backed test sends, health/readiness checks, OpenAPI docs, and a same-origin API tester.

The original plan describes a much larger high-volume notification platform intended to send more
than 50 million personalized emails per week. That plan requires multiple services, queues,
harvesting, distributed delivery, throttling, bounce processing, tracking pixels and redirects,
authentication/RBAC, observability, infrastructure as code, staging/performance testing, and
production-grade CI/CD. Most of those capabilities are not implemented yet.

Current status: **deployed API scaffold, not full notification platform**.

## What Is Implemented

| Plan area | Current codebase status | Evidence |
| --- | --- | --- |
| Controller/API service | Partially implemented. FastAPI exposes templates, campaigns, contacts, events, unsubscribe, and test send endpoints. | `src/email_platform/api/routes.py` |
| PostgreSQL persistence | Implemented for MVP entities. SQLAlchemy models and Alembic migration exist. | `src/email_platform/models/entities.py`, `alembic/versions/0001_initial_schema.py` |
| Template rendering | Partially implemented. Jinja2 renders subject, HTML, and text for test sends. | `src/email_platform/services/templates.py` |
| SMTP/provider abstraction | Partially implemented. Console, SendGrid, and SMTP providers exist. | `src/email_platform/providers/email.py` |
| Test-send workflow | Implemented for a single recipient and existing template. | `src/email_platform/services/sending.py` |
| Event storage | Partially implemented. Events can be manually recorded and listed. | `src/email_platform/services/events.py` |
| Unsubscribe compliance | Partially implemented. Signed unsubscribe token and contact unsubscribe flag exist. | `src/email_platform/services/contacts.py` |
| Health/readiness | Implemented. `/health` and `/ready` exist. | `src/email_platform/main.py` |
| GUI/API integration surface | Partially implemented. OpenAPI docs and `/tester` console exist for manual API testing. | `src/email_platform/api/test_console.py`, `docs/API_INTEGRATION.md` |
| Container/deployment | Partially implemented. Dockerfile, Vercel entrypoint, deployment docs, and live Vercel deployment exist. | `Dockerfile`, `api/index.py`, `vercel.json`, `docs/LIVE_DEPLOYMENT.md` |
| CI checks | Partially implemented. GitHub Actions runs Ruff, MyPy, migrations, and Pytest with Postgres. | `.github/workflows/ci.yml` |

## Major Gaps Against The Original Plan

### 1. Microservice Architecture

Original plan requires seven services:

- Controller Service
- Harvester Service
- Distributor Service
- Sender Service
- Bounce Processor
- Tracker Service
- Admin Service

Current implementation is one FastAPI application. There are no independent service boundaries,
no internal service discovery, and no deployed worker services. `src/email_platform/workers/` is only
a placeholder.

Gap severity: **Critical** for the 50M/week architecture.

Recommended next work:

- Keep the current FastAPI app as the Controller/Admin API boundary.
- Add worker processes for send orchestration before splitting repositories.
- Introduce clear internal modules first: `harvesting`, `distribution`, `delivery`, `tracking`,
  `bounce_processing`.

### 2. Campaign Launch And Fanout

Original plan requires campaign orchestration, segmentation, batching, job creation, and progress
tracking.

Current implementation can create a `Campaign`, but it cannot launch one. `Campaign.audience_query`
is stored as JSON but not evaluated. There is no endpoint such as `POST /api/v1/campaigns/{id}/launch`,
no recipient resolution, no batch job table, and no campaign progress counters.

Gap severity: **Critical**.

Recommended next work:

- Add `campaign_send_jobs` and `email_send_records` tables.
- Add `POST /api/v1/campaigns/{campaign_id}/launch`.
- Resolve recipients from contact attributes and unsubscribe status.
- Enqueue or persist batches for worker processing.

### 3. Harvester Service

Original plan requires workers that process roughly 200 recipients per batch, use read replicas,
execute per-recipient data queries, and support local/external data sources.

Current implementation has no harvester, no batch processing, no read-replica routing, no staging
table, and no data-source mapping per template.

Gap severity: **Critical**.

Recommended next work:

- Add a batch model with status, attempt count, lock timestamp, and cursor/recipient range.
- Add a `required_fields` or `data_requirements` field to templates.
- Add read-replica settings when moving beyond Neon/Vercel MVP hosting.

### 4. Distributor Service

Original plan requires generating SMTP envelopes per recipient after merging dynamic user-specific
data into templates.

Current implementation can render and send a single recipient email through
`POST /api/v1/emails/send` and a test email through `POST /api/v1/tests/send-email`. It does not
create durable envelopes, add campaign headers, add tracking URLs/pixels, or place messages on a
sender queue.

Gap severity: **High**.

Recommended next work:

- Add durable rendered-message/envelope records.
- Add message headers for campaign ID, contact ID, unsubscribe URL, and provider metadata.
- Integrate tracking URL/pixel generation during rendering.

### 5. Sender Service, Retry Logic, And Throttling

Original plan requires SMTP connection pools, async delivery, domain-based throttling, retry logic,
domain-specific limits, transient/permanent error handling, and delivery status updates.

Current implementation sends synchronously through console, SendGrid, or SMTP provider adapters.
There is no connection pool, retry scheduler, throttling table, backoff logic, suppression integration,
or delivery status model.

Gap severity: **Critical** for real volume sending.

Recommended next work:

- Add `email_send_records` with statuses such as queued, sending, sent, failed, suppressed, retried.
- Add `domain_throttle_rules`.
- Add worker loop for queued sends with per-domain rate enforcement.
- Add provider error classification for transient vs permanent failures.

### 6. Bounce Processing And Suppression Lists

Original plan requires processing hard bounces, soft bounces, spam complaints, and maintaining
suppression lists.

Current implementation has `bounced` and `complained` event enum values, but no provider webhook
endpoint, no bounce parser, no suppression table, and no send-blocking behavior based on suppressions.

Gap severity: **Critical** for deliverability and compliance.

Recommended next work:

- Add SendGrid webhook endpoint first.
- Add `suppressions` table with reason, source, scope, and timestamps.
- Block sends to unsubscribed, bounced, and complained contacts.

### 7. Tracker Service

Original plan requires tracking pixels, click redirect URLs, a tracking database, open/click event
recording, and analytics.

Current implementation has manual event ingestion only. There are no pixel endpoints, redirect
endpoints, signed tracking IDs, or campaign/contact rollups.

Gap severity: **High**.

Recommended next work:

- Add `GET /t/open/{tracking_id}.gif` for 1x1 pixel opens.
- Add `GET /t/click/{tracking_id}` for click recording and redirect.
- Add signed tracking IDs to avoid spoofed events.
- Add campaign metrics endpoints.

### 8. Admin Service And GUI Contract

Original plan expects a full admin UI for campaign management, template editing, segmentation, and
metrics.

Current repo provides backend APIs plus a simple `/tester` manual console. The separate SentientMail
GUI has richer concepts such as segments, sends, reports, approvals, template versions, and AI
authoring, but this backend does not expose matching endpoints.

Gap severity: **High** for GUI integration.

Recommended next work:

- Decide whether to adapt SentientMail's `/api` contract or update the GUI to consume `/api/v1`.
- Add endpoints for segments, sends, reports, approvals, and template versions.
- Add update/delete endpoints for existing resources.

### 9. Authentication, Authorization, And Tenancy

Original plan requires OAuth2/JWT, RBAC, roles, user accounts or external identity provider, API
gateway enforcement, and audit logging.

Current implementation has no application-level authentication. Documentation explicitly notes that
auth is not implemented yet. CORS is configurable but currently permissive for testing.

Gap severity: **Critical** before wider exposure.

Recommended next work:

- Add API key or JWT auth immediately.
- Add user/account/role model if the admin GUI will manage real users.
- Add audit logs for mutations.
- Restrict CORS to the production GUI origin.

### 10. Infrastructure And Deployment Platform

Original plan targets AWS ECS/Fargate or EKS, VPC, private subnets, ALB/API Gateway, RDS primary and
replica, tracking database, SQS/RabbitMQ, SNS/EventBridge, S3/CloudFront, and managed secrets.

Current deployment is Vercel plus Neon. This is good for MVP API testing, but it does not provide the
long-running workers, queue consumers, private network design, read replicas, tracking database, or
AWS-native event infrastructure described in the plan.

Gap severity: **High** for production-scale architecture.

Recommended next work:

- Keep Vercel/Neon for API validation and admin integration.
- Move worker-heavy components to Render/Fly.io/AWS ECS when campaign fanout begins.
- Add Terraform or Pulumi before provisioning AWS production resources.

### 11. Observability

Original plan requires centralized logs, metrics, tracing, dashboards, queue-depth alarms,
throughput metrics, delivery metrics, render latency, and DB query timing.

Current implementation has no structured logging, no request IDs, no metrics endpoint, no tracing,
and no dashboard.

Gap severity: **High**.

Recommended next work:

- Add structured JSON logging with request ID and campaign ID.
- Add OpenTelemetry instrumentation.
- Add metrics for endpoint latency, sends, failures, events, and queue depth.

### 12. CI/CD And Release Management

Original plan requires image builds, image scanning, ECR, staging/prod promotion gates, blue/green or
canary deployments, integration tests after deployment, performance tests, and cleanup scripts.

Current CI runs lint/type/test/migrations. Production deploy was executed through Vercel CLI. There
is no staging environment, image registry, security scan, blue/green/canary workflow, performance
testing, or cleanup automation.

Gap severity: **Medium** for MVP, **High** for production.

Recommended next work:

- Add GitHub Actions deployment workflow for Vercel after CI passes.
- Add staging deployment and environment-specific smoke test.
- Add dependency/security scan.
- Add Locust or k6 tests once campaign launch exists.

## Requirement Coverage Matrix

| Original-plan requirement | Coverage | Notes |
| --- | --- | --- |
| Send 50M+ personalized emails/week | Not covered | No distributed workers, queues, throttling, or load tests. |
| Blast campaigns | Partial | Campaign records exist, but no launch/fanout. |
| Triggered campaigns/events | Partial | Manual event ingestion and test send exist; no trigger rules. |
| Extract user-specific relational data | Not covered | Contacts exist, but no harvester or external data mapping. |
| Dynamic templates with Jinja2 | Partial | Rendering exists; no validation/preview/versioning. |
| SMTP delivery | Partial | SMTP adapter exists; synchronous single-send only. |
| Provider delivery via SendGrid | Partial | Adapter exists; no webhook processing. |
| Open tracking | Not covered | No pixel endpoint. |
| Click tracking | Not covered | No redirect endpoint. |
| Bounce processing | Not covered | Enum exists, no processor/webhook/suppression. |
| Unsubscribe handling | Partial | Contact-level unsubscribe flag and signed token exist. |
| Admin API | Partial | Basic backend endpoints exist; missing many admin workflows. |
| Admin GUI | Partial | `/tester` is for manual testing only; real GUI is separate. |
| Segmentation | Minimal | `audience_query` is stored but not executed. |
| Queues/message bus | Not covered | No queue dependency or job model. |
| Read replica | Not covered | Single DB URL plus migration URL only. |
| Tracking database separation | Not covered | Events stored in same primary database. |
| Secrets management | Partial | Environment settings exist; no external secrets manager integration. |
| API gateway/service discovery | Not covered | Vercel routing only. |
| Authentication/RBAC | Not covered | No auth dependencies. |
| Audit logging | Not covered | No audit model or logging. |
| Observability | Minimal | Health/readiness only. |
| Docker/container packaging | Partial | Dockerfile exists. |
| CI/CD | Partial | CI exists; production deployment workflow incomplete. |
| Performance tests | Not covered | No Locust/k6/JMeter tests. |
| Blue/green/canary deployment | Not covered | Not implemented. |

## Recommended Next Execution Plan

### Phase 0: Add A Real Single-Contact Send Endpoint

1. Add a send endpoint that accepts an existing contact, an existing template, and request
   variables.
2. Merge contact fields, contact attributes, and request variables into the template context.
3. Send through the configured provider.
4. Record a sent event for traceability.

### Phase 1: Make The API Safe For GUI Integration

1. Add authentication for all mutation/list endpoints.
2. Restrict CORS to the real GUI URL.
3. Add update/delete endpoints for templates, contacts, and campaigns.
4. Add list envelopes with `items`, `limit`, `offset`, and `total`.
5. Add template preview/validation endpoint.

### Phase 2: Add Campaign Send Lifecycle

1. Add send/job tables.
2. Add campaign launch endpoint.
3. Implement recipient resolution from `audience_query`.
4. Exclude unsubscribed/suppressed contacts.
5. Add worker process for batch processing.

### Phase 3: Add Provider Webhooks And Compliance

1. Add SendGrid webhook ingestion.
2. Add suppression table and send-blocking logic.
3. Add bounce/complaint classification.
4. Add audit logs for admin mutations.

### Phase 4: Add Tracking And Reporting

1. Add open pixel and click redirect endpoints.
2. Add campaign metric rollups.
3. Add contact and campaign event timelines.
4. Add GUI report endpoints.

### Phase 5: Move Toward The Original Scale Architecture

1. Introduce a queue backend.
2. Move workers to long-running compute outside Vercel.
3. Add domain throttling and retry scheduler.
4. Add observability, dashboards, and alerts.
5. Add staging, performance tests, and deployment promotion gates.

## Bottom Line

The current repository is ready for API-level manual testing and early GUI integration. It is not yet
ready for production email campaigns, high-volume sending, or the complete architecture in the
original plan.

The highest-leverage next step is **Phase 0, then Phase 1 plus the first half of Phase 2**: add a real
single-contact send path, secure the API, make the GUI contract comfortable, then add campaign
launch/job/send-record foundations. Those foundations unlock most of the remaining platform work.
