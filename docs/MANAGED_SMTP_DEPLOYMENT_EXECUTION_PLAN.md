# Managed SMTP Deployment Execution Plan

## Purpose

This plan defines how Email Engine moves from a Vercel/Neon control plane to a real owned-MTA
deployment that can send the first real managed-SMTP email. It is provider-neutral until the MTA
hosting provider is selected and verified.

## Deployment Split

Email Engine has two deployment surfaces:

- Control plane: FastAPI, ESP UI assets, scheduler endpoints, and PostgreSQL data. Vercel can keep
  serving this layer, with Neon as the managed database.
- MTA host: Postfix/OpenDKIM containers, SMTP submission listener, outbound SMTP delivery, logs,
  queue state, DSN mailbox paths, DKIM private keys, and TLS private keys. This must run on a VM or
  container host that supports long-lived daemons, stable networking, and SMTP delivery.

Vercel is not the MTA host. It does not provide the persistent TCP services, stable host-level mail
queue, reverse DNS, or outbound TCP port 25 control required for MTA operation.

## Provider Selection Gate

Before provisioning an MTA host, verify the chosen provider with official documentation or support:

- Static IPv4 is available and assignable to the MTA host.
- Outbound TCP port 25 is allowed for direct recipient-MX delivery.
- PTR/rDNS can be configured for the static IPv4.
- Inbound TCP 25 can receive bounce-domain MX traffic if DSNs are delivered by SMTP.
- Inbound TCP 587 can be exposed only to trusted Email Engine worker/network sources where possible.
- Provider abuse and suspension processes are clear enough for production sending.
- Docker Compose or equivalent long-running containers are supported.

If outbound TCP port 25, PTR/rDNS, or static IPv4 cannot be obtained, the provider is No-Go for the
owned MTA role.

## Phase 1: Control Plane Readiness

1. Deploy the API/UI control plane on Vercel or another web platform.
2. Run all Alembic migrations against Neon.
3. Configure control-plane environment variables:
   - `DATABASE_URL`
   - `CORS_ORIGINS`
   - `DEFAULT_FROM_EMAIL`
   - `UNSUBSCRIBE_SECRET`
   - `MANAGED_SMTP_FEEDBACK_SECRET`
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USERNAME`
   - `SMTP_PASSWORD`
   - `SMTP_USE_TLS`
4. Confirm `/ready`, `/api/v1/system/diagnostics`, and
   `/api/v1/managed-smtp/deployment-summary` are reachable.
5. Keep production campaign traffic paused until the MTA host passes smoke and controlled delivery.

## Phase 2: MTA Host Provisioning

1. Provision one Linux VM or persistent container host with static IPv4.
2. Set hostname to the intended MTA hostname, for example `mta-001.example.com`.
3. Configure provider PTR/rDNS for the static IPv4 to match the MTA hostname.
4. Configure firewall rules:
   - Allow inbound TCP 25 when bounce-domain SMTP delivery is required.
   - Allow inbound TCP 587 only from trusted Email Engine worker/network sources where possible.
   - Deny public access to OpenDKIM port 8891.
5. Create host directories for Postfix spool, logs, TLS certs, DKIM keys, DSN Maildir, DSN archive,
   and DSN quarantine.
6. Prepare `infra/managed-smtp/production.env.example` values for this host.
7. Run:

```bash
python scripts/managed_smtp_mta_preflight.py --env-file infra/managed-smtp/production.env.example
```

8. Deploy:

```bash
docker compose --env-file infra/managed-smtp/production.env.example \
  -f infra/managed-smtp/docker-compose.production.yml up --build -d
```

## Phase 3: DNS And Domain Readiness

1. Publish hostname A record.
2. Publish bounce-domain MX record to the MTA host if bounce DSNs use SMTP delivery.
3. Publish SPF for the sending domain and bounce domain.
4. Publish DKIM public key for the active selector.
5. Publish DMARC for the sending domain.
6. In Email Engine, use the managed-SMTP authentication plan and verification APIs to confirm DNS.
7. Do not proceed if DNS verification, PTR/rDNS, or DKIM key alignment fails.

## Phase 4: Inventory Bootstrap

Create or update the Email Engine inventory and route using the bootstrap script:

```bash
MTA_PROVIDER_ACCOUNT_NAME=<provider-account-name> \
MTA_PROVIDER=<provider> \
MTA_REGION=<region> \
MTA_PORT25_STATUS=approved \
MTA_RDNS_STATUS=configured \
MTA_NODE_NAME=mta-001 \
MTA_HOSTNAME=mta-001.example.com \
MTA_PUBLIC_IPV4=203.0.113.10 \
MTA_SUBMISSION_HOST=mta-001.example.com \
MTA_SUBMISSION_PORT=587 \
MTA_AUTH_SECRET_REF=<secret-ref-only> \
MTA_IP_POOL_NAME=internal-test \
MTA_ROUTE_NAME=managed-smtp-primary \
MTA_DOMAIN=example.com \
MTA_BOUNCE_DOMAIN=returns.example.com \
MTA_DKIM_SELECTOR=ee1 \
MTA_DKIM_KEY_REF=<secret-ref-only> \
MTA_ACTIVATE_INVENTORY=true \
MTA_MARK_DOMAIN_VERIFIED=true \
BASE_URL=https://<email-engine-api> \
python scripts/managed_smtp_bootstrap.py
```

The bootstrap must store secret references only. Raw SMTP passwords, provider keys, DKIM private
keys, and TLS private keys remain in deployment secrets or on the MTA host.

## Phase 5: Smoke And Readiness

Run MTA checks from an operator machine or the MTA host:

```bash
python scripts/managed_smtp_mta_smoke.py \
  --host mta-001.example.com \
  --port 587 \
  --starttls \
  --post-readiness \
  --feedback-secret "$MANAGED_SMTP_FEEDBACK_SECRET" \
  --base-url https://<email-engine-api>
```

Then run a seed test with DKIM verification:

```bash
python scripts/managed_smtp_mta_smoke.py \
  --host mta-001.example.com \
  --port 587 \
  --starttls \
  --send-test \
  --from-email sender@example.com \
  --to-email seed@example.com \
  --verify-dkim-crypto \
  --post-feedback \
  --feedback-secret "$MANAGED_SMTP_FEEDBACK_SECRET" \
  --base-url https://<email-engine-api>
```

Review the Delivery Manager managed-SMTP readiness cards and
`/api/v1/managed-smtp/deployment-summary`. Continue only when the selected node, pool, route,
submission credentials, DNS, DKIM, STARTTLS, feedback, and readiness checks are healthy.

## Phase 6: Controlled Delivery

Run controlled delivery against a seed campaign and staging domain policy:

```bash
DOMAIN_POLICY_ID=<domain-policy-id> \
CAMPAIGN_ID=<campaign-id> \
SEED_EMAIL=seed@example.com \
BASE_URL=https://<email-engine-api> \
MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret> \
python scripts/managed_smtp_controlled_delivery.py --send-seed --post-feedback
```

This is the final gate before the first real managed-SMTP email. It verifies diagnostics, managed
SMTP submission credentials, DNS authentication, reputation/compliance status, seed submission, and
signed feedback ingestion.

## Go Criteria

- Provider has approved outbound TCP port 25.
- Static IPv4 and PTR/rDNS are configured and verified.
- MTA containers are running with persistent spool/log/DSN/DKIM/TLS mounts.
- DNS authentication verifies for SPF, DKIM, DMARC, hostname A, and bounce-domain MX where used.
- Email Engine inventory route resolution selects the intended provider account, IP pool, and MTA
  node.
- Submission credentials are configured in the control-plane worker environment.
- SMTP smoke, STARTTLS smoke, seed submission, DKIM verification, feedback ingestion, and readiness
  posting pass.
- Domain policy is not paused, not on compliance hold, and not blocked by reputation or warmup
  health gates.

## No-Go Criteria

- Outbound TCP port 25 is blocked or unapproved.
- PTR/rDNS cannot be configured for the static IPv4.
- The MTA host cannot keep persistent queue, log, DSN, DKIM, and TLS state.
- Submission credentials are missing from the Email Engine deployment.
- DNS authentication is unresolved or mismatched.
- DKIM signing cannot be verified on the captured seed message.
- Managed-SMTP feedback cannot be signed and ingested.
- Readiness checks show active failure, blocklist risk, compliance hold, or warmup hold.

## Rollback

If any smoke, controlled delivery, or first-send gate fails:

1. Pause the domain delivery policy.
2. Pause the managed SMTP delivery route or MTA IP pool.
3. Stop new queue processing for the affected campaign.
4. Keep feedback ingestion and DSN processing running so delayed events are retained.
5. Preserve MTA logs, queue state, DSN archive, readiness evidence, and provider support evidence.
6. Revert `EMAIL_PROVIDER` or route assignment to the previous safe path only after confirming
   suppression and unsubscribe state remains intact.

## Open Execution Inputs

- Chosen MTA hosting provider and region.
- Static IPv4 and PTR/rDNS approval evidence.
- Sending domain and bounce domain.
- TLS certificate source.
- DKIM selector and private-key installation path.
- Control-plane deployment URL.
- Seed campaign, seed mailbox, and go/no-go operator owner.
