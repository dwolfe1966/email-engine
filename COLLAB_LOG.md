# Collab log

Running record of cross-repo changes between **email-engine** (this
repo) and **SentientMail** (`daxym76/SentientMail` — the React UI +
the SpokeoESP demo backend).

Maintained primarily by Chris's Claude instance, but David's Claude is
welcome (encouraged) to append entries too — the goal is that whichever
side picks the work up next has a single place to read what just landed
elsewhere and what they need to do about it.

Newest entries first. Each entry should answer four questions:

1. **What changed** — files, endpoints, contracts.
2. **Why** — design rationale or what audit finding it addresses.
3. **What the other side needs to do** — migrations to run, configs
   to set, contract decisions to make.
4. **Compatibility notes** — breaking changes, deprecations, anything
   that requires coordination before merging in either direction.

---

## 2026-06-10 — Managed SMTP DSN quarantine handling

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- DSN parsing now produces per-message outcomes so valid DSNs and malformed mailbox messages can be
  handled independently.
- `scripts/managed_smtp_dsn_feedback.py` and the maintenance runbook support
  `--quarantine-maildir` / `MANAGED_SMTP_DSN_QUARANTINE`.
- Successfully parsed Maildir messages are archived after successful posting, while malformed or
  non-DSN messages can be moved to a quarantine Maildir for operator review.
- Render and deployment docs now include the DSN quarantine environment variable.

### Why

Production bounce mailboxes can receive malformed DSNs, autoresponders, and unrelated mail. Those
messages should not block valid DSN ingestion or be replayed forever.

### What needs to happen next

- Add operator UI controls for retained provider feedback inspection.
- Add operator tooling for reviewing or purging quarantined DSN mailbox messages.

### Compatibility notes

- No migration is required. Quarantine behavior is opt-in and only applies when a quarantine Maildir
  is configured.

---

## 2026-06-10 — Render managed SMTP recurring jobs

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- `render.yaml` now defines two Docker cron jobs for managed SMTP operations:
  `email-engine-managed-smtp-dsn-ingestion` and `email-engine-managed-smtp-maintenance`.
- The deployment image now copies `scripts/` so cron jobs can invoke the managed-SMTP runbooks.
- Render deployment docs now list the required cron environment variables and schedules.

### Why

Managed SMTP maintenance and bounce-domain DSN ingestion need production scheduler wiring, not just
manual runbook commands.

### What needs to happen next

- Add operator UI controls for retained provider feedback inspection.
- Add quarantine/error handling for malformed DSN messages that cannot be parsed.

### Compatibility notes

- No migration is required. Cron jobs are inactive until their Render environment variables are
  configured.

---

## 2026-06-10 — Managed SMTP DSN mailbox acknowledgement

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- `scripts/managed_smtp_dsn_feedback.py` now supports `--archive-maildir` /
  `MANAGED_SMTP_DSN_ARCHIVE`.
- DSN Maildir messages are moved to the archive only after successful feedback posting.
- `scripts/managed_smtp_maintenance_runbook.py` passes the same archive setting through scheduled
  DSN ingestion.

### Why

Cron-based DSN ingestion needs an acknowledgement step so successfully processed bounce messages do
not get replayed indefinitely.

### What needs to happen next

- Add operator UI controls for retained provider feedback inspection.
- Add recurring job configuration for the chosen production deploy platform.
- Add quarantine/error handling for malformed DSN messages that cannot be parsed.

### Compatibility notes

- No migration is required. Archive behavior is opt-in and only applies to Maildir inputs.

---

## 2026-06-10 — Managed SMTP scheduled maintenance runbook

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `scripts/managed_smtp_maintenance_runbook.py`.
- The runbook calls `/api/v1/domain-delivery-policies/managed-smtp-maintenance`.
- When `MANAGED_SMTP_DSN_PATH` or `--dsn-path` is configured, it also parses and posts DSN feedback
  using the existing DSN bridge.
- Deployment docs now include a cron/scheduler command.

### Why

Managed SMTP maintenance now has multiple operator-safe pieces: blocklist checks, warmup
progression, and DSN ingestion. This gives deployment operators one scheduler entrypoint.

### What needs to happen next

- Add operator UI controls for retained provider feedback inspection.
- Add mailbox cleanup or acknowledgement after successful DSN feedback posting.
- Add recurring job configuration for the chosen production deploy platform.

### Compatibility notes

- No migration is required. The runbook calls existing API endpoints/scripts.

---

## 2026-06-10 — Provider feedback retention list API

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `GET /api/v1/provider-feedback-events/list`.
- The endpoint lists retained provider/MTA feedback events with filters for provider, source, event
  name, email, and provider message ID.
- Responses include retained raw payload JSON, normalized metadata JSON, and idempotency keys.

### Why

Managed SMTP now retains raw feedback for idempotency and evidence. Operators and future UI panels
need a read path to inspect those retained events when debugging bounces, DSNs, and duplicate MTA
feedback.

### What needs to happen next

- Add UI controls for retained provider feedback inspection.
- Add a deploy cron/runbook that runs managed-SMTP maintenance and DSN ingestion on schedule.
- Add mailbox cleanup or acknowledgement after successful DSN feedback posting.

### Compatibility notes

- No migration is required beyond the previously added `0021_provider_feedback_events` table.

---

## 2026-06-10 — Managed SMTP DSN mailbox feedback bridge

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `scripts/managed_smtp_dsn_feedback.py`.
- The script parses RFC822 `message/delivery-status` DSN messages from stdin, a file, or a Maildir.
- DSN `failed` / `5.x.x` outcomes map to `dsn_bounce`; `delayed` / `4.x.x` outcomes map to
  `tempfail`; successful DSN actions map to `delivered`.
- Parsed DSNs can post signed `ManagedSmtpFeedbackEvent` payloads to
  `/api/v1/delivery/managed-smtp/feedback`.

### Why

Bounce-domain routing needs an inbound-mail bridge, not only Postfix log parsing. This lets a
production MTA or mailbox processor feed DSNs into the same durable feedback/idempotency path.

### What needs to happen next

- Add a deploy cron/runbook that runs managed-SMTP maintenance and DSN ingestion on schedule.
- Add mailbox cleanup or acknowledgement after successful DSN feedback posting.
- Add operator views or API list endpoints for retained provider feedback.

### Compatibility notes

- No migration is required for this slice. It reuses the existing managed-SMTP feedback endpoint.

---

## 2026-06-10 — Durable managed SMTP feedback idempotency and retention

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `provider_feedback_events` for raw provider/MTA feedback retention.
- Managed-SMTP feedback now derives provider/source idempotency keys and skips duplicates before
  mutating send records, events, or suppressions.
- Provider feedback ingestion responses now include `duplicate_count`.

### Why

Postfix log tailing, DSN retries, and feedback replays can emit the same delivery event more than
once. Retaining raw feedback with durable idempotency prevents duplicate state transitions and keeps
operator evidence for later debugging.

### What needs to happen next

- Run `alembic upgrade head` in deployed environments.
- Add DSN mailbox/parser integration for bounce-domain inbound mail.
- Add operator views or API list endpoints for retained provider feedback.

### Compatibility notes

- Requires migration `0021_provider_feedback_events`.
- `duplicate_count` is additive on existing ingestion responses.

---

## 2026-06-10 — Managed SMTP DKIM and bounce-domain boundary hardening

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Managed-SMTP delivery now prepares a bounce-domain SMTP envelope sender when the domain policy
  has a bounce domain.
- Delivery attempts and sent events now include managed-SMTP identity metadata such as bounce
  domain, envelope sender, DKIM selector, DKIM key reference, and signing readiness.
- SMTP messages can carry signer hint headers for the MTA boundary.
- The staging Postfix entrypoint supports optional `POSTFIX_DKIM_MILTER` configuration.

### Why

Private DKIM keys should stay at the MTA signer or secret-manager boundary. Email Engine now passes
the routing/signing identity needed by Postfix/OpenDKIM while preserving that private-key boundary.

### What needs to happen next

- Add an external cron/deploy runbook for calling managed-SMTP maintenance on schedule.
- Add durable feedback idempotency and raw MTA feedback retention.
- Add DSN mailbox/parser integration for bounce-domain inbound mail.

### Compatibility notes

- No migration is required. New message fields are additive, and existing providers ignore the
  extra headers/envelope fields unless they support them.

---

## 2026-06-10 — Managed SMTP scheduled maintenance endpoint

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `POST /api/v1/domain-delivery-policies/managed-smtp-maintenance`.
- The endpoint batches blocklist scans and warmup progression across managed-SMTP domain policies.
- It skips non-managed-SMTP routes by default and returns per-policy results for scheduler logs.

### Why

Blocklist checks and warmup progression now have single-policy operator actions. This adds the
cron-friendly entrypoint needed to run them continuously without hand-editing policy metadata.

### What needs to happen next

- Add a deployment runbook or external cron configuration that calls the maintenance endpoint on a
  safe cadence.
- Continue DKIM signing and bounce-domain routing hardening around the managed Postfix boundary.

### Compatibility notes

- No migration is required. The endpoint is additive and reuses existing policy metadata fields.

---

## 2026-06-10 — Managed SMTP warmup progression endpoint

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `POST /api/v1/domain-delivery-policies/{policy_id}/warmup-progress`.
- The endpoint evaluates current domain deliverability against sent-volume, bounce-rate,
  complaint-rate, and blocklist gates.
- Healthy domains can advance warmup stage/order/daily limit; risky domains are held with
  `warmup_hold_reason`, `warmup_status`, and `warmup_audit_log` metadata.

### Why

Managed SMTP needs an operator-controlled path to scale sending volume without manually editing
policy metadata. Warmup progression now has a repeatable API contract and audit trail.

### What needs to happen next

- Add scheduled jobs that run blocklist scans and warmup progression across managed-SMTP policies.
- Continue DKIM signing and bounce-domain routing hardening around the managed Postfix boundary.

### Compatibility notes

- No migration is required. The endpoint is additive and writes existing policy metadata JSON plus
  `warmup_stage` on the domain policy.

---

## 2026-06-10 — Managed SMTP blocklist scan endpoint

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `POST /api/v1/domain-delivery-policies/{policy_id}/blocklist-scan`.
- The endpoint scans configured or supplied IPv4 sending IPs against DNSBL zones through the
  existing DNS resolver abstraction.
- Scan results can persist `blocklist_status`, `blocklist_hits`, `blocklist_checked_at`, and
  `ip_addresses` into domain policy metadata for the reputation dashboard.

### Why

The dashboard and controlled-delivery runbook now understand blocklist readiness; this adds the
operator action that populates that readiness state.

### What needs to happen next

- Add scheduled blocklist scans for managed-SMTP IP pools.
- Add warmup progression automation that advances stages from measured delivery outcomes.
- Continue DKIM signing and bounce-domain routing hardening around the managed Postfix boundary.

### Compatibility notes

- No migration is required. The endpoint is additive and writes only existing policy metadata JSON.

---

## 2026-06-10 — Managed SMTP blocklist and warmup readiness signals

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Expanded the domain reputation dashboard response with sending IPs, blocklist status/hits/check
  timestamp, and warmup status/limits/order fields.
- Active blocklist hits now force reputation risk, and high bounce/complaint rates hold warmup
  progression.
- The controlled-delivery runbook now fails preflight when the dashboard reports listed IPs/domains
  or a warmup hold.

### Why

Managed SMTP needs production readiness gates before scale-up. Operators should see whether the
domain/IP pool has passed blocklist preflight and whether warmup is safe to advance.

### What needs to happen next

- Add automated blocklist scanner jobs that write `blocklist_hits` and `blocklist_checked_at` into
  domain policy metadata.
- Add warmup progression automation that advances stages from measured delivery outcomes.
- Continue hardening DKIM signing and bounce-domain routing around the managed Postfix boundary.

### Compatibility notes

- No migration is required. New dashboard fields are additive and read from existing policy
  metadata / route config.

---

## 2026-06-10 — Managed SMTP Postfix log feedback bridge

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `scripts/managed_smtp_log_feedback.py`.
- The script parses Postfix `smtp` delivery log lines into `ManagedSmtpFeedbackEvent` payloads.
- It maps `sent` to `delivered`, `bounced` to `dsn_bounce`, and `deferred`/`expired` to
  `tempfail`.
- It can print normalized JSON for inspection or post signed feedback to
  `/api/v1/delivery/managed-smtp/feedback`.
- Updated managed-SMTP staging and deployment docs with the log-forwarding command.

### Why

The managed SMTP stack needs MTA-originated delivery feedback, not only manual smoke events, so
Postfix delivery outcomes can feed the same provider-neutral lifecycle, suppression, and analytics
path.

### What needs to happen next

- Add production hardening for DKIM signing, bounce-domain routing, blocklist checks, and IP warmup
  automation.
- Add durable feedback idempotency and raw MTA feedback retention.

### Compatibility notes

- No migration is required. The script emits the existing managed-SMTP feedback contract.

---

## 2026-06-10 — Managed SMTP controlled delivery runbook

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `scripts/managed_smtp_controlled_delivery.py`.
- The script checks diagnostics, domain DNS authentication, reputation dashboard state, and
  compliance hold state before optional seed delivery.
- Optional flags can send a campaign seed test and post signed managed-SMTP feedback smoke.
- Updated managed-SMTP staging and deployment docs with the controlled-delivery command.

### Why

Owned SMTP needs a repeatable low-volume staging gate before production sends. The new runbook keeps
DNS, reputation, compliance, seed delivery, and feedback ingestion in one operator sequence.

### What needs to happen next

- Add DSN/MTA log parser plumbing that emits signed `ManagedSmtpFeedbackEvent` payloads.
- Harden production SMTP with DKIM signing, bounce-domain routing, blocklist checks, and IP warmup
  automation.

### Compatibility notes

- No migration is required. Seed sending and feedback posting are opt-in script flags.

---

## 2026-06-10 — State of the two builds + SentientMail is porting email-engine's delivery layer

**Pushed by:** Chris's Claude
**Repo touched:** `daxym76/SentientMail` (branch `feature/delivery-routing-port`, not merged/deployed). Informational for David's side.

### What changed
- SentientMail has started porting email-engine's provider-neutral delivery layer in
  (tenant-scoped). Slice 1 landed there: `DeliveryRoute` / `DomainDeliveryPolicy` /
  `DeliveryAttempt` models + a migration + schema tests. Additive; not wired into dispatch
  yet. 9-slice plan + analysis live in the SentientMail repo
  (`docs/DELIVERY_ROUTING_PORT_PLAN.md`, `docs/DAVID_EMAIL_ENGINE_CONVERGENCE.md`).

### Why — heads-up on where the two builds actually stand
- `SENTIENTMAIL_GUI_REVIEW_AND_OVERLAP.md` reviewed SentientMail at commit `c548d0e`, which
  predates a lot. Since then SentientMail shipped full SFMC behavior-parity across all 8
  modules, app-level auth (RBAC + sessions + SAML/SSO), multi-tenant entitlements + BU
  isolation + audit hash-chain, A/B testing, and SMS/multichannel — alembic head 104,
  ~1080 tests. So the items the overlap doc lists as "missing in email-engine, port from
  SentientMail" (template versions, segments, send lifecycle, approvals, reports, AI
  authoring, auth, tenants) are already built and far along on the SentientMail side.
- Net: on the app/platform surface the convergence runs the other way from that doc's
  framing. Where email-engine is genuinely ahead and additive is the **deliverability
  layer** — the DeliveryRoute/DomainDeliveryPolicy model, DKIM/DNS-auth onboarding, the
  reputation dashboard, and especially the provider-neutral signed feedback ingestion
  (clean work — SentientMail is adopting that design). That is the piece SentientMail
  lacked (it had only an SES-specific path, go-live deferred).

### What the other side needs to do / weigh in on
- **Role alignment (the ask):** propose email-engine owns the delivery/MTA layer (managed
  SMTP, Postfix, IP/domain reputation, FBL ingestion — where it is ahead) and SentientMail
  stays the platform/app core, instead of each side re-implementing the other. SentientMail
  is porting the delivery design in for now to unblock; if it should instead consume an
  email-engine delivery service over a stable adapter contract, let's define that contract.
- One thing flagged from the read, in case it's useful upstream: in email-engine, route
  selection is decoupled from provider dispatch — process_queued always uses the env-global
  provider, and managed_smtp/ses route types have no provider impl, so the route/policy/
  reputation layer is metadata + gating only today. The SentientMail port wires route ->
  adapter so the route actually steers the send.

### Compatibility notes
- No breaking changes; additive, on a feature branch, not deployed. The ported delivery
  tables are tenant-scoped (email-engine's are not). Contract drift previously raised
  (`/api/v1` vs `/api`, response envelopes, `VITE_AUTH_BASE`) still stands; if both repos
  persist, an OpenAPI contract + base-URL config is the seam.

---

## 2026-06-09 — Managed SMTP compliance controls in Delivery UI

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added a Managed SMTP Domain Compliance panel to the React Delivery page.
- The panel can load domain policies, load a reputation dashboard, apply a compliance hold, and
  release a compliance hold through the new domain-policy endpoints.
- Added equivalent domain policy selector and hold/release controls to legacy `/admin/delivery`.
- Rebuilt the ESP frontend bundle.

### Why

Operators now have a visible control surface for the abuse/compliance stop mechanism added to the
managed-SMTP domain policy API.

### What needs to happen next

- Run low-volume controlled delivery tests after DNS, DKIM, feedback ingestion, reputation dashboard,
  and compliance hold/release controls are verified together.
- Add runbook automation for seed send setup and feedback smoke validation.

### Compatibility notes

- No API migration is required. This consumes the domain policy endpoints added in the previous slice.

---

## 2026-06-09 — Managed SMTP compliance hold controls

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added domain compliance hold and release request contracts.
- Added `/api/v1/domain-delivery-policies/{policy_id}/compliance-hold`.
- Added `/api/v1/domain-delivery-policies/{policy_id}/release-compliance-hold`.
- Compliance holds pause domain policy claiming and persist active hold state plus bounded audit
  history in domain policy metadata.
- The reputation dashboard now reports `compliance_status` and `compliance_reason`, and recommends
  releasing or resolving active holds before managed-SMTP sending resumes.

### Why

Managed SMTP needs an operator-controlled stop mechanism for abuse, complaint, or compliance review
before owned-MTA sending can safely move into controlled delivery tests.

### What needs to happen next

- Surface compliance hold/release controls in the frontend Delivery/Analytics views.
- Run low-volume controlled delivery tests after DNS, DKIM, feedback, reputation, and compliance
  controls are verified.

### Compatibility notes

- No migration is required; hold state and audit entries are stored in existing domain policy metadata.

---

## 2026-06-09 — Managed SMTP reputation dashboard foundation

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `DomainReputationDashboardRead`.
- Added `/api/v1/domain-delivery-policies/{policy_id}/reputation-dashboard`.
- Dashboard output combines domain policy warmup, throttle, IP-pool metadata, authentication
  verification, and observed domain deliverability rollups.
- Added basic reputation status, throttle status, complaint rate, bounce rate, and operator
  recommendations.

### Why

Managed SMTP needs one operator view that connects policy controls with real delivery outcomes
before warmup or production sending can be managed safely.

### What needs to happen next

- Add abuse/compliance controls and audit logging around managed-SMTP operations.
- Use the dashboard contract in the frontend Delivery/Analytics surfaces.

### Compatibility notes

- No migration is required; IP-pool metadata is read from existing route or policy metadata.

---

## 2026-06-09 — Managed SMTP DNS verification and DKIM key management

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added DKIM key generation for domain delivery policies.
- Added `/api/v1/domain-delivery-policies/{policy_id}/dkim-key`.
- The DKIM private key is returned once; policy metadata stores only the key reference, public key,
  and DNS record.
- Added DNS verification for stored domain-authentication plans.
- Added `/api/v1/domain-delivery-policies/{policy_id}/verify-authentication`.

### Why

The managed-SMTP staging path now needs operational checks before seed sends: operators must be
able to generate DKIM material and verify that required DNS records have propagated.

### What needs to happen next

- Add IP pool, warmup, throttle, and reputation dashboards tied to domain policy state.
- Add Postfix/OpenDKIM wiring that consumes the generated key reference in staging.

### Compatibility notes

- No migration is required; key metadata and verification results are stored in existing domain
  policy metadata.
- DNS verification uses system DNS tooling when available and reports `unchecked` rather than
  passing records it cannot query.

---

## 2026-06-09 — Managed SMTP domain authentication onboarding

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added domain-authentication plan schemas for managed-SMTP onboarding.
- Added `/api/v1/domain-delivery-policies/{policy_id}/authentication-plan`.
- The plan generates DKIM, SPF, DMARC, bounce-domain MX, staging-domain MX, and MTA hostname
  A-record instructions.
- Generated plans are persisted under `DomainDeliveryPolicy.metadata_json["domain_authentication"]`.

### Why

The Postfix staging path needs a product-level domain onboarding workflow before real seed testing:
operators need deterministic DNS instructions tied to the domain policy that controls routing and
warmup.

### What needs to happen next

- Add DNS verification so the platform can tell whether DKIM/SPF/DMARC/bounce-domain records are
  actually published.
- Add DKIM private-key management and Postfix/OpenDKIM wiring for the selected selector.

### Compatibility notes

- No schema migration is required; the plan is stored in existing domain policy metadata.

---

## 2026-06-09 — Managed SMTP Postfix staging scaffold

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Selected Postfix as the first owned-MTA staging implementation.
- Added `infra/managed-smtp/` with a minimal Postfix container, `master.cf`, `main.cf`, and
  `docker-compose.staging.yml`.
- Added `scripts/managed_smtp_feedback_smoke.py` to post signed managed-SMTP feedback smoke events.
- Documented the staging flow, Email Engine/MTA responsibility boundary, and required environment
  variables.

### Why

The delivery lifecycle, feedback contract, and signature verification are now stable enough to give
the owned-SMTP work a concrete staging target without prematurely building production
deliverability automation.

### What needs to happen next

- Add DKIM/SPF/DMARC and bounce-domain onboarding around the selected Postfix path.
- Add low-volume staging seed tests once a real staging domain and MTA host are available.

### Compatibility notes

- Existing SendGrid and SMTP adapter behavior is unchanged.
- The Postfix scaffold is staging-only and should not be used for production sending without DNS,
  DKIM, abuse, reputation, and warmup controls.

---

## 2026-06-09 — Managed SMTP feedback signature verification

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `MANAGED_SMTP_FEEDBACK_SECRET`,
  `MANAGED_SMTP_FEEDBACK_REQUIRE_SIGNATURE`, and
  `MANAGED_SMTP_FEEDBACK_SIGNATURE_TOLERANCE_SECONDS` settings.
- Added HMAC-SHA256 verification for `/api/v1/delivery/managed-smtp/feedback`.
- Managed-SMTP feedback callers must sign `{timestamp}.{raw_body}` and send
  `X-Email-Engine-Timestamp` plus `X-Email-Engine-Signature`.
- The managed-SMTP feedback route is public at the GUI-auth middleware layer but rejects unsigned
  requests by default until a secret is configured.
- System diagnostics now reports `managed_smtp_feedback_configured`.

### Why

The owned-MTA feedback endpoint needs to be callable by external MTA/worker infrastructure without
operator cookies, while still rejecting unauthenticated event injection.

### What needs to happen next

- Choose the MTA implementation and build a staging deployment that uses the signed feedback
  contract.
- Add DKIM/SPF/DMARC and bounce-domain onboarding around the selected MTA path.

### Compatibility notes

- SendGrid webhook verification is unchanged.
- Managed-SMTP feedback remains closed by default because
  `MANAGED_SMTP_FEEDBACK_REQUIRE_SIGNATURE=true` and no default secret is configured.

---

## 2026-06-09 — Managed SMTP feedback contract

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `ManagedSmtpFeedbackEvent` for normalized managed-MTA feedback payloads.
- Added protected `/api/v1/delivery/managed-smtp/feedback` ingestion endpoint.
- Managed SMTP feedback now normalizes delivered, bounced, complained, unsubscribed, and deferred
  outcomes into `DeliveryFeedback`.
- Status-only outcomes such as SMTP tempfail/deferral can update send-record lifecycle state
  without creating an email event row.

### Why

The platform now has a first API contract that an owned MTA, DSN parser, bounce mailbox poller, or
feedback-loop processor can use to feed the existing send lifecycle and suppression systems.

### What needs to happen next

- Add managed-SMTP feedback authentication/signature verification before exposing this endpoint to
  an external MTA.
- Choose the MTA/staging deployment path and decide which feedback sources post directly versus
  run as internal workers.

### Compatibility notes

- The managed-SMTP feedback endpoint is currently protected by operator auth, unlike the public
  SendGrid webhook endpoint that has SendGrid signature verification.

---

## 2026-06-09 — Provider-neutral delivery feedback ingestion

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `DeliveryFeedback` as the normalized feedback item contract for provider and managed-SMTP
  delivery outcomes.
- Added `FeedbackIngestionService` to persist normalized feedback as email events, send-record
  lifecycle status updates, and suppressions.
- Refactored SendGrid webhook ingestion so SendGrid only normalizes payloads, then delegates
  persistence to the shared feedback service.
- Existing `/api/v1/provider-webhooks/sendgrid` response counts stay compatible.

### Why

Managed SMTP needs to feed DSNs, bounce mailbox parsing, feedback-loop complaints, and MTA logs
through the same persistence path as third-party provider webhooks.

### What needs to happen next

- Add a managed-SMTP feedback ingestion contract that converts DSN/bounce/complaint/MTA log inputs
  into `DeliveryFeedback`.
- Decide which feedback inputs are synchronous API payloads, background-polled mailboxes, or
  append-only MTA log streams.

### Compatibility notes

- SendGrid webhook API shape is unchanged; only internal normalization and persistence ownership
  moved.

---

## 2026-06-09 — Delivery lifecycle status expansion

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added send-record lifecycle statuses for `submitted`, `deferred`, `delivered`, `bounced`,
  `complained`, and `unsubscribed`.
- Delivery processing now records accepted adapter submissions as `submitted` and retryable
  failures as `deferred`.
- Provider feedback events now promote records into delivered, bounced, complained, or unsubscribed
  lifecycle states.
- Analytics, send-job progress, overview, and Delivery Manager counts roll richer lifecycle states
  into existing queue, accepted, failed, and suppression buckets.
- Added Alembic revision `0020_send_lifecycle_statuses`.

### Why

Managed SMTP needs a durable lifecycle that separates adapter acceptance from final inbox outcome
and keeps transient deferrals distinct from records that have never been attempted.

### What needs to happen next

- Normalize SendGrid webhook handling behind a provider-neutral feedback service so managed SMTP,
  SendGrid, and future adapters emit the same feedback contract.
- Add managed-SMTP feedback ingestion for DSNs, bounce mailbox events, complaints, and MTA logs.

### Compatibility notes

- Public counters remain backward compatible by folding `deferred` into queued, `submitted` and
  `delivered` into sent/accepted, `bounced` into failed, and complaints/unsubscribes into
  suppression review.

---

## 2026-06-09 — Delivery Manager audit surfacing

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Delivery Manager now surfaces `claim_blocked` and `dead_lettered` delivery-attempt audit rows.
- Added React ESP admin action to load attempt audit rows filtered by selected send record or send
  job.
- Added React ESP admin action to dead-letter the selected send record.
- Added a Delivery Attempt Audit panel showing reason, route, recipient domain, record ID, and
  domain policy reference.
- Static `/admin/delivery` also gained Dead-letter Record and Load Attempt Audit actions.

### Why

The send engine now persists queue-control and dead-letter audit rows. Operators need those rows
visible in Delivery Manager so policy pauses, throttles, and terminal queue decisions are
explainable.

### What needs to happen next

- Expand send statuses and transition logic.
- Normalize SendGrid webhooks through a provider-neutral feedback service.
- Continue toward managed-SMTP feedback ingestion and the deeper `DeliveryAdapter` boundary.

### Compatibility notes

- No API or schema changes in this slice.
- Rebuilt `frontend/dist` assets are included.

---

## 2026-06-09 — Dead-letter queue controls

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added terminal `dead_lettered` send-record status.
- Added `POST /api/v1/email-send-records/{send_record_id}/dead-letter` for operator terminal
  queue control.
- Dead-lettering writes a `delivery_attempts` audit row with route type `queue_control`, route key
  `dead_lettered`, previous status, and operator reason.
- Send-job progress now includes `dead_lettered_count` and treats dead-lettered records as
  processed.
- Requeue remains available for dead-lettered records that need recovery.

### Why

Operators need a terminal state for records that should not keep cycling through retries or remain
ambiguously failed. This creates the first explicit terminal queue-control path before broader
delivery lifecycle expansion.

### What needs to happen next

- Surface claim-blocked and dead-letter audit rows in Delivery Manager.
- Expand send statuses and transition logic.
- Continue toward provider-neutral feedback ingestion and the deeper `DeliveryAdapter` boundary.

### Compatibility notes

- Adds Alembic revision `0019_dead_letter_send_status`.
- Existing delivery behavior is unchanged unless an operator explicitly dead-letters a record.
- PostgreSQL enum downgrade leaves the value in place because enum values cannot be dropped safely
  without type recreation.

---

## 2026-06-09 — Queue-control audit persistence

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Delivery queue claiming now persists a `delivery_attempts` audit row when a queued record is not
  claimed because of domain policy controls.
- Audit rows use status `claim_blocked`, route type `queue_control`, and route key equal to the
  block reason such as `domain_policy_paused`, `domain_policy_max_per_minute`, or
  `domain_policy_max_concurrent`.
- `DeliveryRunRead` now includes skipped count and skipped record IDs.
- Throttle counters now count only actual submission attempts (`submitting`/`submitted`) so audit
  rows do not extend throttle windows.

### Why

Delivery Manager and future AI/operator workflows need an explainable record of why queued sends
were not claimed. This makes domain throttles and pauses inspectable instead of invisible.

### What needs to happen next

- Add Delivery Manager UI surfacing for `claim_blocked` rows.
- Add dead-letter state and explicit terminal queue controls.
- Continue expanding send lifecycle states before the deeper `DeliveryAdapter` implementation.

### Compatibility notes

- No migration in this slice; it reuses `delivery_attempts`.
- Existing records remain queued when blocked by policy controls.
- Existing delivery behavior remains unchanged for domains without a policy.

---

## 2026-06-09 — Domain queue-control enforcement

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added explicit pause/resume shortcut APIs for delivery routes and domain delivery policies.
- Delivery queue claiming now consults domain delivery policies before moving records from
  `queued` to `sending`.
- Paused domain policies, `max_per_minute`, and `max_concurrent` limits prevent records from being
  claimed while leaving them queued for later processing.
- Claiming accounts for records reserved in the current batch so one process run does not exceed a
  low per-domain cap.

### Why

Domain policies are now active queue-control inputs, not only planning metadata. This is required
before managed SMTP warmup, domain throttling, route failover, and emergency pause workflows can be
trusted operationally.

### What needs to happen next

- Add persisted throttle/skip audit events so Delivery Manager can explain why queued records were
  not claimed.
- Add dead-letter states and terminal queue controls.
- Continue expanding send lifecycle states before the deeper `DeliveryAdapter` implementation.

### Compatibility notes

- No migration in this slice; it uses the existing delivery route and domain policy tables.
- Existing records remain queued when blocked by policy controls.
- Existing delivery behavior remains unchanged for domains without a policy.

---

## 2026-06-09 — Domain delivery policy foundation

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added domain delivery policies as the third managed SMTP/send-engine foundation slice.
- Domain policies store exact recipient domain, preferred delivery route, throttle hints,
  warmup stage, pause window, and metadata.
- Route selection now prefers a matching non-paused domain policy route before falling back to
  active provider routes or `EMAIL_PROVIDER`.
- Delivery attempts now include domain policy ID, warmup stage, and throttle hint metadata when a
  policy drives selection.

### Why

This is the first control-plane layer needed for provider/MTA routing by recipient domain,
managed-SMTP warmup, domain-specific throttling, and emergency domain pause controls.

### What needs to happen next

- Enforce domain policy throttle hints in queue claiming and processing.
- Add explicit pause/resume shortcuts for routes and domain policies.
- Then continue toward the deeper `DeliveryAdapter` boundary so route-selected providers execute
  from route config instead of only global settings.

### Compatibility notes

- Existing delivery behavior remains compatible because policy selection falls back to route/default
  settings when no matching policy exists or a policy is paused.
- Adds Alembic revision `0018_domain_delivery_policies`.
- Adds operator APIs under `/api/v1/domain-delivery-policies`.

---

## 2026-06-09 — Delivery routes foundation

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added first-class delivery routes as the next managed SMTP/send-engine foundation slice.
- Delivery routes model the future provider/MTA route layer with route type, status, priority,
  config, secret reference, and metadata.
- Added route selection for delivery processing. For now it prefers an active route matching the
  configured `EMAIL_PROVIDER` and falls back to settings when no route exists.
- Delivery attempts now record selected route type/key/source metadata.

### Why

This creates the control-plane table needed before managed SMTP, domain policies, fallback routes,
warmup, and provider/MTA failover can become real operator workflows.

### What needs to happen next

- Add domain delivery policies for per-domain route selection, throttles, warmup stages, and pause
  windows.
- Then introduce the deeper `DeliveryAdapter` boundary so route-selected providers can execute from
  route config instead of only global settings.

### Compatibility notes

- Existing delivery behavior remains compatible because route selection falls back to
  `EMAIL_PROVIDER`.
- Adds Alembic revision `0017_delivery_routes`.
- Adds operator APIs under `/api/v1/delivery-routes`.

---

## 2026-06-09 — Explicit managed SMTP direction

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Product direction clarified: one foundation item is to build, deploy, and operate an Email
  Engine-managed SMTP server and reputation layer rather than depending on paid relays such as
  SendGrid or Amazon SES as the primary delivery architecture.
- Added `docs/MANAGED_SMTP_SEND_ENGINE_PLAN.md` with current foundation, target architecture,
  lifecycle states, data-model tasks, service/API tasks, MTA deployment track, and the first
  implementation slice.

### Why

The next SMTP/send-engine foundation work should assume first-party SMTP ownership is a core
platform objective. Third-party providers can remain useful adapters, migration paths, or fallback
routes, but they should not define the long-term delivery model.

### What needs to happen next

- Walk the owned SMTP/send-engine foundation task from architecture through first implementation
  slice: queue model, provider/MTA boundary, retry policy, bounce and complaint ingestion,
  deliverability telemetry, and operator controls.
- Start the first code slice by adding a `DeliveryAttempt` model/read schema and teaching
  `DeliveryService.process_queued` to persist one attempt per provider submission.

### Compatibility notes

- Adds a new `delivery_attempts` table through Alembic revision `0016_delivery_attempts`.
- Adds a new operator API: `GET /api/v1/delivery-attempts/list`.
- Existing send-record APIs and provider behavior remain compatible.

---

## 2026-06-08 — ESP platform-readiness UI pass and current handoff

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Template Editor polish landed before this handoff:
  - one collapsible `Template Controls` preflight container above the workspace,
  - workspace module tabs moved above status messages,
  - status messages default open,
  - hidden Feedback pane can be restored with a global `+ Feedback` row.
- A platform-foundation documentation pass was added across the ESP admin UI. Recent pushed commits include:
  - `9913ada` Docs API lifecycle readiness panel
  - `c4a9f94` Integrations connector roadmap
  - `92938c8` Data connector sync contract
  - `3eca8ad` Delivery send-engine operations contract
  - `81f454a` Compliance feedback policy contract
  - `f8f4cf2` Analytics deliverability signal contract
  - `d025aef` AI workflow agent contract
  - `909dbff` Settings platform governance contract
  - `edbf9b7` Contacts relationship contract
  - `27652c5` Audience segmentation contract

### Why

David raised that major foundations are still missing even while UI polish is improving: data connectors across RDBMS/warehouse/NoSQL/API sources, multi-entity joins, client-owned entities, owned SMTP server, send queues, bounce queues, deliverability feedback, and ever-present AI agents. The recent pass makes those gaps visible in the operator UI instead of hiding them in backlog notes.

### What needs to happen next

Recommended next backlog slice: move from UI readiness panels into implementation planning for one foundation area. The best next candidate is the **owned SMTP/send engine** because Delivery, Compliance, Analytics, Integrations, Docs, Settings, and Overview now all point at the same gap.

Practical next steps:

1. Draft backend implementation plan for owned SMTP server, MTA policy, send queues, retry policy, bounce classification, complaint handling, and feedback ingestion.
2. Decide whether the first implementation target is internal queue tables/APIs, SMTP submission/MTA integration, or bounce/complaint event ingestion.
3. Convert the chosen foundation into schema/API tasks and tests before adding more UI panels.

### Compatibility notes

- No known breaking API changes in this pass; most changes are React UI copy/panels, CSS, tests, and rebuilt `frontend/dist` assets.
- Repeated verification pattern was:
  - `npm run build`
  - focused frontend workflow test for the touched page
  - `.venv/bin/pytest tests/test_api_contract.py`
- Existing untracked local files were intentionally left untouched:
  - `docs/ESP Research and Design.pdf`
  - `docs/OpenAI API Key.rtf`
  - `docs/SendGrid.rtf`
  - `docs/twilio_2FA_recovery_code.txt`
  - `docs/visual-design-*.png`
  - `tests/Milkbar_Email_List_6_4_.xlsx - subs*.csv`
  - `tests/random_people_100.csv`

---

## 2026-05-25 (later 2) — Auth router mounted under BOTH `/api/v1/auth/*` and `/api/auth/*`

**Pushed by:** Chris's Claude
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- `src/email_platform/api/auth.py` — `APIRouter` declaration no
  longer carries `prefix='/api/v1/auth'`. The handlers still
  declare paths as `/login`, `/logout`, `/me` relative to whatever
  prefix the mount supplies.
- `src/email_platform/main.py` — `include_router(auth_router)`
  now happens twice:

  ```python
  app.include_router(auth_router, prefix='/api/v1/auth')
  app.include_router(auth_router, prefix='/api/auth')
  ```

  Both prefixes share one set of handlers, one schema, one DB read.

### Why

The shared SentientMail React UI in `daxym76/SentientMail/ui/`
hardcodes `/api/auth/login` (no `/v1`). David's Vercel
deployment of that UI talks to email-engine, which used to mount
auth only at `/api/v1/auth/login`. Result: every login attempt
on `ui-eight-rho.vercel.app` returned 404 → UI fell back to
the generic "Invalid email or password" message → looked like a
credentials problem when it was actually a routing problem.

This is the "Option A" of the two paths called out in the prior
COLLAB_LOG entry (the other being a UI-side `VITE_AUTH_BASE`
env). Option A wins on:
- Cheaper to ship (no UI rebuild, no Vercel env coordination).
- Lower-blast-radius (additive — David's existing `/v1` clients
  untouched).
- Future-proof if the API path conventions ever diverge —
  the shared UI keeps one path; backend-specific clients keep
  their `/v1` namespace.

### What the SentientMail side needs to do

Nothing. The shared UI was already calling `/api/auth/...`; this
makes that call succeed on David's deployment too.

### Compatibility notes

- **Backward-compatible.** Anyone hitting `/api/v1/auth/login` on
  email-engine still hits the same handler, same response.
- **Routing-only change.** No handler logic touched, no schema
  changed, no DB migration. `pytest` clean (19 passing).
- **Cookie scope unchanged.** Same `esp_session` name, same
  HttpOnly/Secure/SameSite=Lax shape, same Max-Age.
- **No effect on email-engine's other routers** (admin_console,
  template_editor, etc.) — auth is still the only router with
  this dual-mount.
- **Future cleanup:** if email-engine ever decides to retire the
  `/v1` prefix on auth (or move it to `/v2`), the dual-mount
  makes that a one-line change.

---

## 2026-05-25 (later) — Spokeo side: nginx basic-auth dropped + `require_user` enforced on all non-auth/non-health routes

**Pushed by:** Chris's Claude
**Repos touched:** `daxym76/SentientMail` only. email-engine
unchanged this round, but worth knowing about so the contract
expectations don't drift.

### What changed (Spokeo backend, for context)

- The nginx basic-auth wall in front of `esp.cpew.me` is gone.
  App-level cookie auth is now the only gate.
- Every router except `health` and `auth` mounts with
  `dependencies=[Depends(require_user)]`. Anonymous calls return
  401 with `WWW-Authenticate: Cookie`.

### Why email-engine should care

When you're ready to do the equivalent move on email-engine
(drop whatever fronting layer protects it — Vercel auth /
Cloudflare access / etc. — and rely on app-level cookies),
mirror the pattern:

```python
from fastapi import Depends
from email_platform.services.auth import require_user  # to be written

protected = [Depends(require_user)]
app.include_router(router, dependencies=protected)
app.include_router(compat_router, dependencies=protected)
app.include_router(admin_console_router, dependencies=protected)
app.include_router(test_console_router, dependencies=protected)
app.include_router(template_editor_router, dependencies=protected)

# Stay public:
app.include_router(auth_router)
# (health endpoint is at app-level, also public)
```

### What needs to happen first on this side

`require_user` doesn't exist in `services/auth.py` yet — only the
service-layer primitives. Add a FastAPI `Depends` helper, mirror
of our spokeo `auth.py:optional_user / require_user`:

```python
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session
from email_platform.db.session import get_db
from email_platform.models.entities import User
from email_platform.services.auth import SESSION_COOKIE_NAME, lookup_session

def optional_user(
    db: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> User | None:
    if not token:
        return None
    row = lookup_session(db, token)
    if row is None:
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    db.commit()
    return user

def require_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user
```

Drop that in `services/auth.py` (or a new `api/deps.py` if you
prefer to keep services/ free of FastAPI imports — our Spokeo
side has it co-located in `auth.py` for now).

### Compatibility notes

- No contract change visible to the UI on either side. Cookie
  shape is identical; only the gating layer moved from
  nginx → app.
- If you have an in-flight workstream that depends on
  unauthenticated access to email-engine endpoints from outside
  the GUI (e.g. a tester / curl-from-CI flow), it'll need a
  session cookie or an API-key alternative (separate workstream,
  not in scope today).

---

## 2026-05-25 — App-level auth on both backends + shared `<LoginCanvas>` UI

**Pushed by:** Chris's Claude
**Repos touched:** `daxym76/SentientMail` (commits `b10cb99` + merge
`94cf3cc`), `dwolfe1966/email-engine` (commit `2831995c`).

### What changed in email-engine (this repo)

- `User` + `UserSession` ORM models added to `models/entities.py`,
  matching the existing `PGUUID` / `Mapped` / `StrEnum` style.
- `services/auth.py` — argon2id hashing, session token mint/hash/
  lookup/revoke, sliding-expiry refresh, lockout helpers, and the
  `authenticate()` entry point used by the route.
- `api/auth.py` — `POST /api/v1/auth/login`,
  `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`. Mounted in
  `main.py` before the other routers so it appears first in OpenAPI.
- Alembic migration `0015_users_and_sessions` creates the `users` and
  `user_sessions` tables.
- `scripts/seed_user.py` — admin CLI to seed the first operator.
- `argon2-cffi` added to `pyproject.toml` and `requirements.txt`.

### What changed in SentientMail (`daxym76/SentientMail`)

- Shared React UI: new `/login` route outside the shell
  (`ui/src/canvas/LoginCanvas.tsx`), new `AuthProvider` context
  (`ui/src/state/authContext.tsx`), new `<ProtectedRoute>` wrapping
  everything else (`ui/src/components/ProtectedRoute.tsx`), new auth
  API wrappers in `ui/src/lib/api.ts` (`authLogin`, `authLogout`,
  `authMe`, `apiFetch`, `AuthError`). TopNav shows signed-in email +
  Sign-out button.
- SpokeoESP backend (`src/spokeo_esp/`) got the same auth scaffold
  as email-engine but at `/api/auth/...` (no `/v1` prefix) and
  CORS narrowed from `allow_origins=["*"]` to a per-env allowlist.

### Auth contract (shared between both backends)

```
POST /api/v1/auth/login       (this backend)
POST /api/auth/login          (SpokeoESP backend)
  body: { email: string, password: string }
  resp: { user: { id, email, display_name, role } }
  side effect: Set-Cookie: esp_session=<32-byte token>; HttpOnly;
               Secure (non-local); SameSite=Lax; Max-Age=2592000; Path=/

POST /api/v1/auth/logout      (this backend)
POST /api/auth/logout         (SpokeoESP backend)
  resp: 204 No Content
  side effect: Set-Cookie: esp_session=; Max-Age=0
  Idempotent — repeated calls with no/expired cookie still 204.

GET  /api/v1/auth/me          (this backend)
GET  /api/auth/me             (SpokeoESP backend)
  resp: { user: { id, email, display_name, role } } | 401
```

- **Password storage:** argon2id (library defaults), stored in
  `users.password_hash`. Plaintext never logged or written to disk.
- **Cookie token:** 32-byte URL-safe random (`secrets.token_urlsafe(32)`).
  Only `sha256(token)` is stored in the DB so a read-only DB compromise
  doesn't grant active sessions.
- **Lockout:** 5 failed attempts → account locked for 30 minutes. State
  on the user row (`failed_login_count` + `locked_until`); resets on
  successful login or operator password reset.
- **Sliding expiry:** every authenticated request bumps `last_seen_at`;
  when remaining time < 7 days, `expires_at` extends by another 30.
- **Constant-time decoy:** the "no such user" branch runs an argon2
  verify against a stable decoy hash so login response timing doesn't
  leak account existence.

### What needs to happen next on email-engine

1. **Run the migration** against the deployed Postgres:
   ```
   alembic upgrade head
   ```
2. **Seed the first user** (replace email/password):
   ```
   python scripts/seed_user.py --email you@domain --password '<strong-secret>'
   ```
3. **Decide the UI ⇄ email-engine path mapping.** The shared UI today
   calls `/api/auth/login` etc. (no `/v1`). Two options when wiring
   the UI against email-engine:
   - **(A)** Add a no-prefix alias mount on email-engine —
     `app.include_router(auth_router, prefix='')` or a second router
     that mirrors the `/v1` paths under `/api/auth/...`.
   - **(B)** Add a build-time `VITE_AUTH_BASE` env to the UI
     (default `/api/auth`) so the SentientMail build sets it to
     `/api/v1/auth` and the SpokeoESP build leaves the default.
   - Recommendation: **B**. It's the future-correct shape since
     other API paths will diverge too. ~10-line change in
     `ui/src/lib/api.ts`.
4. **Apply auth to existing mutating routes** when you're ready to
   make auth mandatory. The auth endpoints are exposed but existing
   routes (`/api/v1/templates/...`, `/api/v1/campaigns/...`, etc.)
   are still unauthenticated, intentionally, so demos aren't broken
   mid-rollout. A FastAPI `Depends()` on a `require_user` factory
   would do it — happy to write that side too if you want me to
   take that part.

### Compatibility notes

- **No breaking changes** to existing endpoints. Auth is additive.
- The `users` and `user_sessions` table names use plural snake_case
  consistent with everything else in `entities.py`. The Python class
  is `User` and `UserSession` (User is singular — `UserSession`
  avoids confusion with the SQLAlchemy `Session` and the existing
  `CampaignSendJob` naming pattern).
- `argon2-cffi` is the only new dep. It compiles a small C extension
  at install — no runtime fetches. Wheels are published for all the
  Python versions email-engine targets.

---

## How to add a new entry

When you push anything cross-cutting (UI contract changes, schema
changes, security fixes, new endpoints the other side would want to
mirror, env vars, deploy changes), add a new entry at the TOP of
this file with today's date.

Brief is fine — the goal is "what does the other side need to know"
not "what did I do today." Skip the entry if it's purely local to
one repo and doesn't affect the other.
