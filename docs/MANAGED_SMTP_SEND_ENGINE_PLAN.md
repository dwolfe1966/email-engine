# Managed SMTP And Send Engine Plan

## Direction

Email Engine should build, deploy, and operate its own SMTP server and reputation layer as a
first-party platform service. Paid providers such as SendGrid, Amazon SES, Mailgun, and Postmark
should remain optional adapters, migration paths, customer-choice routes, or temporary fallback
routes. They should not define the long-term delivery architecture.

The immediate engineering goal is not to deploy an MTA first. The first goal is to make Email
Engine own the send lifecycle: queue state, retry policy, idempotency, suppression checks, event
normalization, deliverability telemetry, and operator controls. Once that internal contract is
stable, the managed SMTP implementation can plug into the same adapter boundary as external
providers.

## Current Foundation

Already shipped:

- `CampaignSendJob` and `EmailSendRecord` models.
- Queued campaign fanout records.
- On-demand database-backed delivery processing through `DeliveryService.process_queued`.
- Provider abstraction in `email_platform.providers.email`.
- Console, SendGrid, and basic SMTP provider implementations.
- Retry delay and max-attempt fields on send records.
- Suppression checks during campaign/journey fanout.
- SendGrid webhook ingestion with normalized email events and suppressions.
- Delivery manager APIs for listing, requeueing, skipping, and processing queued records.
- Analytics surfaces over send records and email events.

Important gaps:

- Send statuses are too coarse for a first-party queue and SMTP lifecycle.
- Delivery attempts are now stored as first-class records, but the attempt model still needs deeper
  provider/MTA response normalization.
- Queue rows do not yet capture routing decisions such as provider, domain, IP pool, or MTA route.
- Provider/MTA responses are stored only as a provider message ID and error string.
- Bounce and complaint ingestion is provider-specific, not a managed-SMTP contract.
- Domain policy records now capture route, throttle hints, warmup stage, and pause windows, but
  active enforcement is still pending.
- No dead-letter state, pause/resume controls, enforced throttles, or reputation signals.
- No owned-MTA deployment plan or operational runbook.

## Target Architecture

Email Engine should own these layers:

1. Campaign, journey, or API send intent.
2. Immutable launch/send manifest.
3. Per-recipient queue records.
4. Suppression and consent checks.
5. Template rendering and tracking/unsubscribe variable injection.
6. Delivery route selection.
7. Submission to a provider or managed SMTP adapter.
8. Attempt persistence and retry/dead-letter decisions.
9. Event normalization for sent, delivered, deferred, bounced, complained, opened, clicked, and
   unsubscribed events.
10. Analytics, reputation, and operator controls.

The managed SMTP/MTA layer should own:

1. SMTP transport.
2. DNS/MX delivery.
3. Low-level SMTP response capture.
4. DKIM signing and outbound identity where appropriate.
5. Bounce mailbox or DSN parsing.
6. Feedback-loop ingestion handoff.
7. MTA logs and operational telemetry.

The boundary between them should be a stable delivery adapter contract. The managed SMTP adapter and
third-party adapters should all return normalized submission results and normalized feedback events.

## Proposed Lifecycle States

Expand the send lifecycle beyond the current `queued`, `sending`, `sent`, `failed`, `suppressed`,
and `skipped` states.

Recommended state set:

- `queued`: record is eligible for processing.
- `rendering`: template and variables are being prepared.
- `ready_to_send`: rendered payload is complete and waiting for route/submission.
- `submitting`: adapter/MTA submission is in progress.
- `submitted`: accepted by adapter/MTA, final delivery result pending.
- `deferred`: transient delivery failure; retry is scheduled.
- `delivered`: confirmed delivered by provider/MTA feedback.
- `bounced`: terminal bounce.
- `complained`: spam complaint or feedback-loop complaint.
- `unsubscribed`: recipient unsubscribed.
- `failed`: terminal application or provider failure.
- `dead_lettered`: terminal queue failure requiring operator review.
- `suppressed`: blocked before send by suppression/consent policy.
- `skipped`: intentionally skipped by operator.

Compatibility note: the existing API can initially keep mapping terminal delivery success to `sent`
for older clients while the backend introduces richer internal states.

## Data Model Tasks

First schema slice:

1. Add `delivery_attempts`.
   - `id`
   - `send_record_id`
   - `send_job_id`
   - `campaign_id`
   - `attempt_number`
   - `provider`
   - `route_type`
   - `route_key`
   - `status`
   - `provider_message_id`
   - `smtp_response_code`
   - `smtp_response`
   - `error_message`
   - `started_at`
   - `completed_at`
   - `metadata_json`
2. Add `delivery_routes`.
   - `id`
   - `name`
   - `route_type`: `managed_smtp`, `sendgrid`, `ses`, `smtp_relay`, `console`
   - `status`: `active`, `paused`, `disabled`
   - `priority`
   - `config`
   - `secret_ref`
   - `metadata_json`
3. Add richer routing fields to `email_send_records`.
   - `route_type`
   - `route_key`
   - `domain`
   - `priority`
   - `locked_at`
   - `lock_token`
   - `dead_letter_reason`
4. Add `domain_delivery_policies`.
   - `domain`
   - `route_id`
   - `max_per_minute`
   - `max_concurrent`
   - `warmup_stage`
   - `paused_until`
   - `metadata_json`
5. Add `delivery_feedback_events` if `email_events` is not enough for raw provider/MTA feedback.
   - Keep normalized analytics events in `email_events`.
   - Store raw feedback payloads and idempotency keys in the feedback table.

## Service And API Tasks

1. Replace direct provider use in `DeliveryService` with a delivery adapter boundary.
   - `DeliveryAdapter.submit(message, context) -> DeliverySubmissionResult`
   - `DeliveryAdapter.normalize_feedback(payload) -> list[DeliveryFeedbackEvent]`
2. Split delivery processing into explicit steps.
   - claim queue records
   - render message
   - select route
   - submit
   - persist attempt
   - decide next state
   - emit normalized event
3. Add route selection service.
   - domain policy lookup
   - fallback route support
   - paused route handling
   - future account/campaign/domain throttling hooks
4. Add feedback ingestion service.
   - provider-neutral endpoint/service path
   - SendGrid adapter remains supported
   - managed SMTP bounce/DSN parser can feed the same service later
5. Add operator APIs.
   - pause/resume route
   - pause/resume domain
   - requeue deferred/dead-letter records
   - list delivery attempts
   - inspect raw feedback
   - list domain policy and route health

## Managed SMTP Deployment Track

The MTA choice should happen after the internal delivery contract is stable. Candidate approaches:

- Haraka: Node.js SMTP server, plugin-friendly, useful for custom policy and instrumentation.
- ZoneMTA: queue/retry oriented outbound MTA, useful for bulk delivery and pool management.
- Postal: broader mail platform with operational tooling, heavier footprint.
- Postfix: mature and reliable transport, but custom product integration often lives around it
  rather than inside it.

Selection criteria:

- DKIM signing support and domain identity management.
- Bounce and DSN handling.
- Feedback-loop ingestion path.
- Queue visibility and control.
- IP pool and route control.
- Domain throttling and warmup support.
- Log/export integration.
- Operational complexity.
- Security posture and abuse controls.

Initial deployment should use a constrained staging domain and low-volume seed list. Production use
requires DNS, DKIM, SPF, DMARC, bounce domain, abuse monitoring, blocklist checks, warmup policy,
and emergency pause controls.

## First Implementation Slice

Recommended first code slice:

1. Add the architecture doc and handoff note. **Done.**
2. Add tests that document the richer lifecycle contract. **Done.**
3. Add `DeliveryAttempt` model and read schema. **Done.**
4. Teach `DeliveryService.process_queued` to persist an attempt for every provider submission.
   **Done.**
5. Add route/context fields to attempt metadata without changing the public send API yet. **Done.**
6. Add `/api/v1/email-send-records/{id}/attempts` or a filtered `/api/v1/delivery-attempts/list`
   endpoint. **Done.**
7. Keep current providers working through the existing `EmailProvider` while preparing the deeper
   `DeliveryAdapter` interface. **Done.**
8. Add tests for successful submission, retry scheduling, terminal failure, and attempt persistence.
   **Done.**

## Second Implementation Slice

Recommended second code slice:

1. Add `DeliveryRoute` model and read/write schemas. **Done.**
2. Add `/api/v1/delivery-routes`, `/api/v1/delivery-routes/list`, and
   `/api/v1/delivery-routes/{route_id}` operator APIs. **Done.**
3. Add route selection service that prefers an active route matching the configured provider and
   falls back to `EMAIL_PROVIDER` when no route exists. **Done.**
4. Record selected route type/key/source on delivery attempts. **Done.**
5. Keep per-route credentials/provider execution for a later adapter slice, so existing deployments
   remain compatible. **Done.**

This slice gives operators and future SMTP work a durable attempt history without requiring an MTA
deployment decision up front.

## Third Implementation Slice

Recommended third code slice:

1. Add `DomainDeliveryPolicy` model and read/write schemas. **Done.**
2. Add `/api/v1/domain-delivery-policies`, `/api/v1/domain-delivery-policies/list`, and
   `/api/v1/domain-delivery-policies/{policy_id}` operator APIs. **Done.**
3. Teach route selection to prefer a matching, non-paused exact-domain policy route. **Done.**
4. Record policy ID, warmup stage, and throttle hints on delivery attempts. **Done.**
5. Keep throttle enforcement for a later queue-control slice. **Done.**

## Follow-On Slices

1. Add route pause/resume shortcuts and explicit policy pause/resume controls.
2. Enforce domain policy throttles in queue claiming/processing.
3. Expand send statuses and transition logic.
4. Normalize SendGrid webhooks through a provider-neutral feedback service.
5. Add managed-SMTP feedback ingestion contract.
6. Choose MTA implementation and build a staging deployment.
7. Add DKIM/SPF/DMARC/bounce-domain onboarding workflow.
8. Add IP pool, warmup, throttle, and reputation dashboards.
9. Add abuse/compliance controls and audit logging.
10. Run low-volume controlled delivery tests before production sends.
