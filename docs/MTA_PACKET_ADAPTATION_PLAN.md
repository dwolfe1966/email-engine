# MTA Packet Adaptation Plan

Date: 2026-06-13

## Purpose

The `docs/smtp-architecture/email_engine_mta_codex_packet/` packet is useful architecture input for
Email Engine's managed SMTP/MTA path. It should not be applied directly. The packet assumes a
different repository shape, TypeScript service contracts, and a raw SQL migration path, while this
repo already has Python services, Pydantic contracts, Alembic migrations, delivery routes, domain
delivery policies, managed SMTP readiness checks, managed SMTP feedback ingestion, and a Postfix /
OpenDKIM deployment scaffold.

Use the packet as a blueprint. Port the concepts into the existing Email Engine control plane and
reuse the managed SMTP assets that are already checked in.

## Current Repo Foundation

Already present in Email Engine:

- `delivery_routes` with route type `managed_smtp`.
- `domain_delivery_policies` with route assignment, throttles, warmup stage, pause windows, and
  metadata.
- `managed_smtp_readiness_checks` plus summary, trend, alert, and notification APIs.
- Provider-neutral feedback ingestion, including signed managed SMTP feedback.
- DSN, Postfix log, smoke, readiness notification, and controlled-delivery scripts.
- `infra/managed-smtp/` staging and production-shape Postfix/OpenDKIM scaffolds.
- First-send runbook at `docs/FIRST_MANAGED_SMTP_SEND_RUNBOOK.md`.

The next work should extend this foundation rather than create a parallel MTA subsystem.

## Packet Concept Mapping

| Packet concept | Repo-native adaptation |
| --- | --- |
| `mta_provider_accounts` | New table is likely justified. It should represent provider account, abuse contact, support case, port 25 status, rDNS status, and provider-level kill switch. |
| `mta_nodes` | New table is likely justified. It should represent a concrete MTA host with hostname, public IP, provider account, status, submission endpoint, readiness timestamp, and metadata. |
| `mta_ip_pools` | New table is likely justified, but keep first version small. It should represent shared, warmup, quarantine, transactional, and dedicated pool boundaries. |
| `mta_ip_pool_nodes` | New join table is likely justified once more than one node or pool exists. It can be introduced with the first node model if simple. |
| `tenant_delivery_profiles` | Do not add wholesale yet. Map this initially to `delivery_routes` plus `domain_delivery_policies`. Revisit after account/customer tenancy is explicit. |
| `tenant_sending_domains` | Do not add wholesale yet. Extend or normalize `domain_delivery_policies` metadata for bounce domain, DKIM selector/key ref, verification status, compliance status, and MTA routing. |
| `mta_readiness_checks` | Reuse `managed_smtp_readiness_checks`. Add `mta_node_id`, `provider_account_id`, or `ip_pool_id` later only if reporting needs it. |
| `warmup_plans` / `warmup_plan_steps` | Defer separate tables. Current warmup state lives on domain policy metadata and service logic. Add configurable plans only when the single-domain warmup path is working. |
| TypeScript route contracts | Convert the decision tree and block reasons into Pydantic schemas and Python service methods. |
| Raw SQL migration | Do not apply directly. Write Alembic migrations that fit current naming, enum, model, and downgrade conventions. |
| Packet MTA Docker files | Use as reference only. Prefer existing `infra/managed-smtp/` assets because they already include production-shape env validation, DSN paths, OpenDKIM entrypoints, and runbooks. |
| Packet Terraform scaffold | Use as provider research input. It is not deployable as-is because most resources are commented out and provider-specific details are missing. |

## Implementation Order

### Slice 1: Adaptation and Inventory

Goal: create the minimum control-plane inventory needed to model one real MTA node without
disrupting existing delivery routes.

Deliverables:

- Alembic migration for `mta_provider_accounts`, `mta_nodes`, `mta_ip_pools`, and
  `mta_ip_pool_nodes`.
- SQLAlchemy entities.
- Pydantic read/create/update contracts.
- Admin APIs to list/create/update/pause/resume provider accounts, nodes, and pools.
- Tests for CRUD and pause/resume behavior.

Constraints:

- Default provider accounts, nodes, and pools to non-production or paused states.
- Do not route traffic through a node merely because it exists.
- Keep secrets in `secret_ref` fields, not raw database columns.

### Slice 2: Route Resolution

Goal: let Email Engine explain whether a managed SMTP send is routable and, if so, which MTA node
would be used.

Deliverables:

- Python route-resolution service integrated with `DeliveryRouteService`.
- Block reasons adapted from the packet:
  - `GLOBAL_KILL_SWITCH`
  - `ROUTE_PAUSED`
  - `DOMAIN_NOT_READY`
  - `POOL_PAUSED`
  - `NO_HEALTHY_MTA_NODE`
  - `WARMUP_LIMIT_EXCEEDED`
  - `BOUNCE_THRESHOLD_EXCEEDED`
  - `COMPLAINT_THRESHOLD_EXCEEDED`
  - `COMPLIANCE_HOLD`
- Read-only API that returns either the selected route or the blocking reason.
- Tests that prove paused route, paused pool, failed readiness, and warmup limits block sends.

Constraints:

- The first version can be advisory/read-only.
- Do not change production send behavior until route resolution is tested and operator-visible.

### Slice 3: Delivery Handoff

Goal: submit one controlled Email Engine send through a selected managed SMTP route.

Deliverables:

- Worker/send-service handoff from selected route to SMTP submission config.
- Attempt metadata that records route, domain policy, provider account, pool, node, and MTA host.
- Envelope sender generation using the bounce domain from domain policy metadata.
- DKIM selector/key-ref headers preserved for MTA-side signing.
- Tests covering selected-route submission metadata and fallback behavior.

Constraints:

- Start with seed/internal test traffic only.
- Keep marketing sends blocked unless suppression and unsubscribe enforcement are satisfied.

### Slice 4: Cloud MTA Deployment

Goal: deploy one real MTA node and run the first full smoke path.

Deliverables:

- Choose provider and region after direct verification of outbound port 25 policy, rDNS support,
  abuse-process requirements, and static IPv4 availability.
- Provision one Linux VM with static IPv4.
- Configure DNS: A, PTR/rDNS, SPF, DKIM, DMARC, and bounce-domain MX.
- Deploy `infra/managed-smtp/docker-compose.production.yml` with pinned host mounts and secrets.
- Run preflight, SMTP smoke, STARTTLS smoke, DKIM verification, feedback ingestion, and readiness
  posting.
- Capture provider verification evidence in the new provider/node records.

Constraints:

- Vercel remains the API/UI/control plane.
- The MTA must run on a VM or provider that supports persistent SMTP daemons and outbound port 25.
- Do not use broad production traffic until seed delivery, DKIM, SPF, DMARC, DSN, and readiness all
  pass.

## Cloud Deployment Decision Notes

The packet's provider matrix is a starting point, not final authority. Before provisioning, verify
current policies with official provider docs and, where needed, support tickets.

Provider requirements for first MTA host:

- Static public IPv4.
- Outbound TCP port 25 to major recipient MX hosts.
- PTR/rDNS control.
- Inbound 25 if receiving bounce-domain MX traffic.
- Inbound 587 restricted to Email Engine worker/network sources where possible.
- Clear abuse contact and suspension/remediation process.
- Ability to run Docker Compose or equivalent long-lived services.

Vercel should not host the MTA because it does not run persistent TCP daemons and is not suited for
SMTP listener/queue processes. It can continue hosting the app/control plane if the MTA submits
readiness and feedback events back to the API over HTTPS.

## Immediate Next Coding Task

Implement Slice 1: MTA provider/node/pool inventory.

Keep the migration narrow and additive. The first schema should model infrastructure inventory and
operational status only. It should not duplicate domain policy, readiness, or warmup tables that
already exist.

Recommended first tables:

- `mta_provider_accounts`
- `mta_nodes`
- `mta_ip_pools`
- `mta_ip_pool_nodes`

Recommended initial APIs:

- `GET /api/v1/managed-smtp/provider-accounts/list`
- `POST /api/v1/managed-smtp/provider-accounts`
- `PATCH /api/v1/managed-smtp/provider-accounts/{id}`
- `GET /api/v1/managed-smtp/nodes/list`
- `POST /api/v1/managed-smtp/nodes`
- `PATCH /api/v1/managed-smtp/nodes/{id}`
- `GET /api/v1/managed-smtp/ip-pools/list`
- `POST /api/v1/managed-smtp/ip-pools`
- `PATCH /api/v1/managed-smtp/ip-pools/{id}`

This gives us the control-plane inventory needed to begin the cloud-container deployment work
without waiting for full multi-tenant route automation.
