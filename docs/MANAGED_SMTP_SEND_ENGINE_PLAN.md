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
- SendGrid webhook ingestion through a provider-neutral feedback ingestion service with normalized
  email events, send-record lifecycle status updates, and suppressions.
- Delivery manager APIs for listing, requeueing, skipping, and processing queued records.
- Analytics surfaces over send records and email events.

Important gaps:

- Send statuses now cover submission, deferral, delivery, bounce, complaint, unsubscribe, and
  dead-letter outcomes, but `rendering`, `ready_to_send`, and `submitting` remain attempt-level
  concepts rather than durable send-record states.
- Delivery attempts are now stored as first-class records, but the attempt model still needs deeper
  provider/MTA response normalization.
- Queue rows do not yet capture routing decisions such as provider, domain, IP pool, or MTA route.
- Provider/MTA responses are stored only as a provider message ID and error string.
- Bounce and complaint persistence now uses a provider-neutral feedback service, and a signed
  managed-SMTP feedback API accepts normalized DSN, complaint, unsubscribe, delivery, and deferral
  inputs.
- Domain policy records now capture route, throttle hints, warmup stage, and pause windows, and
  queue claiming enforces pause/per-minute/concurrent controls.
- Queue-control skips now persist audit rows in `delivery_attempts`, and send records can be moved
  into a terminal `dead_lettered` state. Reputation signals are still pending.
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

Compatibility note: API analytics and progress counters roll the richer states into existing
`queued`, `sent`, `failed`, and `suppressed` buckets for older dashboard clients.

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

The first staging MTA choice is Postfix, deployed as a constrained outbound transport in
`infra/managed-smtp/`. Email Engine owns send queue state, domain policy, signed feedback ingestion,
suppression creation, and analytics rollups; Postfix owns SMTP transport.

Candidate approaches considered:

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

Initial deployment should use the checked-in Postfix staging scaffold, a constrained staging domain,
the domain authentication plan and verification endpoints, DKIM key management, and a low-volume
seed list. Production use still requires SPF/DMARC alignment automation, bounce-domain processing,
abuse monitoring, blocklist checks, warmup policy, and emergency pause controls.

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

## Fourth Implementation Slice

Recommended fourth code slice:

1. Add explicit route pause/resume shortcut APIs. **Done.**
2. Add explicit domain policy pause/resume shortcut APIs. **Done.**
3. Enforce paused domain policies during queue claiming. **Done.**
4. Enforce `max_per_minute` during queue claiming. **Done.**
5. Enforce `max_concurrent` during queue claiming. **Done.**
6. Keep skipped records queued so they can be claimed after pause/throttle windows clear. **Done.**

## Fifth Implementation Slice

Recommended fifth code slice:

1. Persist queue-control audit rows when records are not claimed because of domain policy controls.
   **Done.**
2. Use `claim_blocked` delivery-attempt status with `queue_control` route metadata for blocked
   records. **Done.**
3. Expose skipped count and skipped record IDs in `DeliveryRunRead`. **Done.**
4. Keep throttle counters limited to actual submission attempts so audit rows do not extend throttle
   windows. **Done.**

## Sixth Implementation Slice

Recommended sixth code slice:

1. Add terminal `dead_lettered` send-record status. **Done.**
2. Add `/api/v1/email-send-records/{send_record_id}/dead-letter` operator API. **Done.**
3. Persist a `delivery_attempts` audit row when an operator dead-letters a record. **Done.**
4. Keep requeue support for dead-lettered records that need recovery. **Done.**
5. Include `dead_lettered_count` in send-job progress and count it as processed. **Done.**

## Seventh Implementation Slice

Recommended seventh code slice:

1. Surface `claim_blocked` and `dead_lettered` delivery-attempt audit rows in Delivery Manager.
   **Done.**
2. Add Delivery Manager action for loading attempt audit rows filtered by selected record or job.
   **Done.**
3. Add Delivery Manager action for dead-lettering a selected record. **Done.**
4. Add static `/admin/delivery` hooks for attempt audit loading and dead-lettering. **Done.**

## Eighth Implementation Slice

Recommended eighth code slice:

1. Add durable send-record statuses for `submitted`, `deferred`, `delivered`, `bounced`,
   `complained`, and `unsubscribed`. **Done.**
2. Mark accepted adapter submissions as `submitted` instead of terminal `sent`. **Done.**
3. Mark retryable delivery failures as `deferred` and keep them eligible for queue claiming.
   **Done.**
4. Map provider feedback events into lifecycle statuses while preserving normalized email events.
   **Done.**
5. Roll richer lifecycle states into existing analytics, progress, overview, and Delivery Manager
   counters for compatibility. **Done.**

## Ninth Implementation Slice

Recommended ninth code slice:

1. Add a provider-neutral `DeliveryFeedback` contract for delivery feedback items. **Done.**
2. Add `FeedbackIngestionService` to persist normalized feedback as email events, send-record
   lifecycle updates, and suppressions. **Done.**
3. Refactor SendGrid webhook handling so SendGrid payloads normalize into the shared feedback
   service instead of owning persistence directly. **Done.**
4. Preserve existing `/api/v1/provider-webhooks/sendgrid` response counts and payload behavior.
   **Done.**

## Tenth Implementation Slice

Recommended tenth code slice:

1. Add `ManagedSmtpFeedbackEvent` request schema for normalized MTA/DSN/complaint feedback.
   **Done.**
2. Add `/api/v1/delivery/managed-smtp/feedback` ingestion endpoint. **Done.**
3. Normalize managed-SMTP delivery, bounce, complaint, unsubscribe, and deferral events into
   `DeliveryFeedback`. **Done.**
4. Allow status-only feedback such as deferrals to update send-record lifecycle state without
   requiring an email event row. **Done.**

## Eleventh Implementation Slice

Recommended eleventh code slice:

1. Add `MANAGED_SMTP_FEEDBACK_SECRET` and signature tolerance settings. **Done.**
2. Add HMAC-SHA256 verification for `/api/v1/delivery/managed-smtp/feedback`. **Done.**
3. Require `X-Email-Engine-Timestamp` and `X-Email-Engine-Signature` headers for managed-SMTP
   feedback. **Done.**
4. Make the managed-SMTP feedback route public at the GUI-auth middleware layer but closed by
   default until the feedback secret is configured. **Done.**
5. Surface `managed_smtp_feedback_configured` in system diagnostics. **Done.**

## Twelfth Implementation Slice

Recommended twelfth code slice:

1. Select Postfix as the first managed-SMTP staging MTA. **Done.**
2. Add a constrained Postfix container scaffold under `infra/managed-smtp/`. **Done.**
3. Add `docker-compose.staging.yml` for local or VM-based MTA staging. **Done.**
4. Add a signed managed-SMTP feedback smoke script. **Done.**
5. Document the staging flow and Email Engine/MTA responsibility boundary. **Done.**

## Thirteenth Implementation Slice

Recommended thirteenth code slice:

1. Add domain-authentication request/read schemas for DKIM, SPF, DMARC, and bounce-domain DNS
   onboarding. **Done.**
2. Add `/api/v1/domain-delivery-policies/{policy_id}/authentication-plan`. **Done.**
3. Generate deterministic DKIM, SPF, DMARC, return-path/bounce MX, staging-domain MX, and MTA
   hostname A-record instructions. **Done.**
4. Persist the generated plan under `DomainDeliveryPolicy.metadata_json["domain_authentication"]`.
   **Done.**

## Fourteenth Implementation Slice

Recommended fourteenth code slice:

1. Add DKIM key generation for domain delivery policies. **Done.**
2. Return the generated private key once and persist only key reference, public key, and DNS record
   metadata. **Done.**
3. Add `/api/v1/domain-delivery-policies/{policy_id}/dkim-key`. **Done.**
4. Add DNS verification for stored domain-authentication plans. **Done.**
5. Add `/api/v1/domain-delivery-policies/{policy_id}/verify-authentication`. **Done.**

## Fifteenth Implementation Slice

Recommended fifteenth code slice:

1. Add a managed-SMTP domain reputation dashboard schema. **Done.**
2. Add `/api/v1/domain-delivery-policies/{policy_id}/reputation-dashboard`. **Done.**
3. Combine domain policy warmup/throttle/IP-pool metadata with authentication verification state.
   **Done.**
4. Fold observed domain deliverability metrics into the policy dashboard. **Done.**
5. Return reputation status, throttle status, complaint rate, bounce rate, and operator
   recommendations. **Done.**

## Sixteenth Implementation Slice

Recommended sixteenth code slice:

1. Add domain-level abuse/compliance hold and release request contracts. **Done.**
2. Add `/api/v1/domain-delivery-policies/{policy_id}/compliance-hold`. **Done.**
3. Add `/api/v1/domain-delivery-policies/{policy_id}/release-compliance-hold`. **Done.**
4. Persist active compliance hold state and bounded audit history on domain policy metadata.
   **Done.**
5. Surface active compliance hold status and recommendations in the reputation dashboard.
   **Done.**

## Seventeenth Implementation Slice

Recommended seventeenth code slice:

1. Surface managed-SMTP domain compliance controls in the React Delivery page. **Done.**
2. Add domain policy loading, reputation dashboard loading, compliance hold, and compliance release
   frontend actions. **Done.**
3. Add legacy `/admin/delivery` controls for domain policy selection, dashboard loading, hold, and
   release. **Done.**
4. Rebuild the ESP frontend bundle with the new controls. **Done.**

## Eighteenth Implementation Slice

Recommended eighteenth code slice:

1. Add a controlled-delivery runbook script for managed-SMTP staging. **Done.**
2. Sequence diagnostics, domain DNS verification, reputation dashboard, and compliance readiness
   checks before seed sends. **Done.**
3. Support explicit optional seed test send and signed feedback smoke steps. **Done.**
4. Document the controlled-delivery command in staging and deployment docs. **Done.**

## Nineteenth Implementation Slice

Recommended nineteenth code slice:

1. Add a Postfix MTA log parser for managed-SMTP feedback. **Done.**
2. Map Postfix `sent`, `bounced`, `deferred`, and `expired` delivery statuses into
   `ManagedSmtpFeedbackEvent` payloads. **Done.**
3. Support signed posting to `/api/v1/delivery/managed-smtp/feedback`. **Done.**
4. Document staging log forwarding from `/var/log/mail.log`. **Done.**

## Twentieth Implementation Slice

Recommended twentieth code slice:

1. Extend the managed-SMTP reputation dashboard with blocklist status, blocklist hits, sending IPs,
   and warmup progression state. **Done.**
2. Treat active blocklist hits as reputation risk and warmup health failures. **Done.**
3. Gate the controlled-delivery runbook on listed IPs/domains and warmup holds. **Done.**
4. Document the expanded readiness contract for production managed-SMTP preflight. **Done.**

## Follow-On Slices

1. Add production hardening for DKIM signing, bounce-domain routing, automated blocklist scanners,
   and IP warmup progression jobs.
2. Add durable feedback idempotency and raw MTA feedback retention.
