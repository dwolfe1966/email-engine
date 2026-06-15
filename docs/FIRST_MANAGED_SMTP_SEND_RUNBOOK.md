# First Managed SMTP Send Runbook

This runbook defines the provider-agnostic sequence for sending the first real email through Email
Engine's managed SMTP path. Use it after the MTA hosting provider and deployment model are selected.

## Goal

Send one controlled seed email through an Email Engine-managed SMTP route, signed by our MTA,
published to recipient MX infrastructure, and traced back into Email Engine readiness and feedback
surfaces.

## Preconditions

- A hosting provider has been selected for the MTA host.
- The provider allows outbound SMTP to recipient MX servers, especially TCP port `25`.
- A static public IPv4 address is assigned to the MTA host.
- Reverse DNS/PTR is configured for the MTA hostname.
- The sending domain and bounce domain are selected.
- DNS can be edited for SPF, DKIM, DMARC, MX, and related records.
- Email Engine API/UI and database are already deployed.
- `MANAGED_SMTP_FEEDBACK_SECRET` is configured on the Email Engine API and operational scripts.
- A seed mailbox is available for receipt/capture testing.

## Target Topology

- ESP/API/UI: existing app host.
- Database: existing PostgreSQL/Neon database.
- MTA host: dedicated VM/server running Postfix and OpenDKIM.
- Worker path: Email Engine send processing submits via authenticated SMTP submission to the MTA.
- Feedback path: Postfix logs and DSN mailbox events post signed managed-SMTP feedback into Email
  Engine.
- Readiness path: MTA smoke checks publish durable readiness evidence into Delivery Manager.
- Alert path: readiness notification dispatcher posts raw or Slack webhook payloads when active
  readiness alerts exist.

## Provisioning Checklist

1. Provision a Linux VM/server with a static public IPv4 address.
2. Configure provider firewall/security groups:
   - inbound `25/tcp` if the host receives MX/DSN traffic
   - inbound `587/tcp` for authenticated submission from approved Email Engine workers
   - inbound `22/tcp` or provider-native access for administration
   - outbound `25/tcp` to recipient MX servers
   - outbound `443/tcp` to Email Engine API for feedback/readiness posting
3. Configure reverse DNS/PTR for the MTA hostname.
4. Create DNS records:
   - `A smtp.example.com -> <MTA public IPv4>`
   - `MX returns.example.com -> smtp.example.com`
   - SPF for the sending domain including the MTA IP
   - DKIM public key for the selected selector
   - DMARC policy for the sending domain
5. Generate or install TLS certificate files for Postfix submission.
6. Generate DKIM private/public key material and store private keys outside the repo.
7. Create durable host paths for:
   - Postfix spool
   - Postfix logs
   - DSN Maildir
   - DSN archive Maildir
   - DSN quarantine Maildir
   - OpenDKIM private keys
   - TLS cert/key files

## MTA Host Setup

Prepare `infra/managed-smtp/production.env.example` values for the chosen domain/host, then run:

```bash
python scripts/managed_smtp_mta_preflight.py --env-file infra/managed-smtp/production.env.example
```

Start the production MTA stack:

```bash
docker compose --env-file infra/managed-smtp/production.env.example \
  -f infra/managed-smtp/docker-compose.production.yml up --build -d
```

Confirm the services are healthy and the host exposes only the intended ports.

## Email Engine Configuration

1. Bootstrap the Email Engine control-plane mapping for the first MTA:

   ```bash
   BASE_URL=https://<email-engine-api> \
   MTA_PROVIDER=aws \
   MTA_PROVIDER_ACCOUNT_NAME=aws-managed-smtp-staging \
   MTA_PROVIDER_REGION=us-west-2 \
   MTA_NODE_NAME=mta-001 \
   MTA_HOSTNAME=smtp.example.com \
   MTA_PUBLIC_IPV4=<MTA public IPv4> \
   MTA_AUTH_SECRET_REF=secret/managed-smtp/mta-001/submission \
   MTA_IP_POOL_NAME=internal-test \
   MTA_SENDING_DOMAIN=example.com \
   MTA_BOUNCE_DOMAIN=returns.example.com \
   MTA_DKIM_SELECTOR=ee1 \
   MTA_DKIM_KEY_REF=vault://dkim/example.com/ee1 \
   python scripts/managed_smtp_bootstrap.py
   ```

2. Confirm the response includes provider account, node, IP pool, route, domain policy, and route
   resolution next steps.
3. Configure worker SMTP submission credentials in the Email Engine deployment environment:
   - `SMTP_USERNAME`
   - `SMTP_PASSWORD`
   - `SMTP_USE_TLS=true`
4. Confirm the route and domain policy appear in Delivery Manager.
5. Load Managed SMTP Deployment in Delivery Manager and confirm the MTA node, IP pool, route, and
   readiness status are visible.
6. Keep the domain in low-volume/warmup mode before any non-seed traffic.
7. After provider port 25, PTR/rDNS, DNS authentication, MTA deployment, and readiness checks pass,
   rerun bootstrap with:

   ```bash
   MTA_ACTIVATE_INVENTORY=true \
   MTA_MARK_DOMAIN_VERIFIED=true \
   MTA_PORT25_STATUS=approved \
   MTA_RDNS_STATUS=configured \
   python scripts/managed_smtp_bootstrap.py
   ```

When a managed-SMTP route resolves successfully, the delivery worker submits through the resolved
MTA `submission_host` and `submission_port` while using the deployment SMTP credentials above. The
inventory `auth_secret_ref` remains a reference only and should not contain raw credentials.

## Smoke Sequence

Run public MTA readiness checks before sending a seed message:

```bash
BASE_URL=https://<email-engine-api> \
MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret> \
python scripts/managed_smtp_mta_smoke.py \
  --host smtp.example.com \
  --port 587 \
  --require-starttls \
  --starttls-handshake \
  --post-readiness \
  --json
```

Expected result:

- SMTP banner is visible.
- EHLO succeeds.
- STARTTLS is advertised.
- STARTTLS handshake succeeds.
- A readiness check appears in Delivery Manager.

## First Seed Send

Send one seed message through the MTA:

```bash
DEFAULT_FROM_EMAIL=sender@example.com \
SEED_EMAIL=seed@example.net \
BASE_URL=https://<email-engine-api> \
MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret> \
python scripts/managed_smtp_mta_smoke.py \
  --host smtp.example.com \
  --port 587 \
  --require-starttls \
  --starttls-handshake \
  --send-test \
  --post-feedback \
  --post-readiness \
  --json
```

Expected result:

- Postfix accepts the message for the seed recipient.
- The seed mailbox receives the message.
- Email Engine records managed-SMTP feedback.
- Delivery Manager readiness remains passing or produces actionable evidence.

## DKIM Verification

Capture the received seed email as RFC822/`.eml`, then verify DKIM:

```bash
python scripts/managed_smtp_mta_smoke.py \
  --skip-smtp-probe \
  --verify-dkim-message /path/to/captured-seed.eml \
  --dkim-domain example.com \
  --dkim-selector ee1 \
  --require-dkim-from-domain \
  --verify-dkim-crypto \
  --json
```

Expected result:

- Captured message contains a matching `DKIM-Signature`.
- DKIM domain and selector match the domain policy.
- Cryptographic DKIM verification passes against DNS.

## Feedback Verification

For MTA logs:

```bash
tail -F /var/log/mail.log \
  | MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret> \
    BASE_URL=https://<email-engine-api> \
    python scripts/managed_smtp_log_feedback.py --post -
```

For DSN mailbox ingestion:

```bash
MANAGED_SMTP_FEEDBACK_SECRET=<shared feedback secret> \
BASE_URL=https://<email-engine-api> \
python scripts/managed_smtp_dsn_feedback.py --post \
  --archive-maildir /path/to/archive-Maildir \
  --quarantine-maildir /path/to/quarantine-Maildir \
  /path/to/Maildir
```

Expected result:

- Delivered, bounced, deferred, and complaint-like signals normalize into provider-neutral feedback.
- Hard bounces and complaints update suppression state.
- Malformed DSNs are quarantined instead of replayed forever.

## Readiness And Alert Verification

Load Delivery Manager and confirm:

- Managed SMTP Readiness has the latest smoke check.
- Summary, trend, alert evidence, and notification payload are populated.
- Readiness notification dispatcher exits quietly when no alert exists.
- If a failure is forced, dispatcher produces the expected raw or Slack webhook payload.

Dry-run notification dispatch:

```bash
BASE_URL=https://<email-engine-api> \
MANAGED_SMTP_READINESS_WEBHOOK_FORMAT=slack \
python scripts/managed_smtp_readiness_notify.py --dry-run
```

## Go/No-Go Criteria

Go only if:

- Provider permits Outbound SMTP delivery.
- PTR, SPF, DKIM, and DMARC are correct.
- MTA smoke check passes.
- Seed message is received.
- DKIM crypto verification passes.
- Feedback ingestion path works.
- Delivery Manager shows readiness and no critical alert.
- Suppression path is verified with at least one controlled bounce or synthetic feedback event.

No-go if:

- Port `25` is blocked.
- PTR does not match the MTA hostname.
- DKIM verification fails.
- DSN/log feedback cannot be posted.
- The MTA is on a listed or obviously dirty IP.
- The provider's acceptable-use or abuse process is unclear.

## After First Send

1. Keep volume at seed-only until the provider/IP/DNS posture is stable.
2. Start warmup with very small limits.
3. Monitor bounces, deferrals, complaints, readiness checks, and blocklist scans.
4. Only expand traffic after multiple clean readiness windows.
5. Record the chosen provider topology and any provider-specific commands in a follow-up deployment
   runbook.
