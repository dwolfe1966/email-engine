# Managed SMTP Staging

This scaffold is the first concrete owned-MTA deployment path. It chooses Postfix for staging
because Postfix is mature, operationally familiar, and works well as a constrained outbound
transport while Email Engine owns queue state, feedback normalization, and operator controls.

It is not a production deliverability stack yet. Production still needs DKIM signing, SPF/DMARC
alignment, bounce-domain routing, abuse controls, IP pool policy, warmup automation, queue
observability, and blocklist monitoring.

## Components

- `postfix/`: minimal Postfix container for constrained staging.
- `docker-compose.staging.yml`: standalone MTA compose file with SMTP on host port `2525` and
  submission on host port `2587`.
- `scripts/managed_smtp_feedback_smoke.py`: signs and posts a sample feedback event to Email
  Engine's managed-SMTP feedback endpoint.
- `scripts/managed_smtp_controlled_delivery.py`: runs the controlled-delivery readiness sequence:
  diagnostics, domain DNS verification, reputation/compliance dashboard, optional seed send, and
  optional signed feedback smoke.
- `scripts/managed_smtp_log_feedback.py`: parses Postfix `smtp` delivery log lines into
  `ManagedSmtpFeedbackEvent` payloads and can post them with the same signed feedback contract.
- `scripts/managed_smtp_dsn_feedback.py`: parses RFC822 DSN bounce messages from stdin, a file, or
  a Maildir into `ManagedSmtpFeedbackEvent` payloads.

## Staging Flow

1. Deploy Email Engine with `MANAGED_SMTP_FEEDBACK_SECRET` configured.
2. Start the staging MTA:

   ```bash
   docker compose -f infra/managed-smtp/docker-compose.staging.yml up --build -d
   ```

3. Configure Email Engine for staging submission:

   ```text
   EMAIL_PROVIDER=smtp
   SMTP_HOST=<mta-host>
   SMTP_PORT=2587
   SMTP_USE_TLS=false
   DEFAULT_FROM_EMAIL=no-reply@<staging-domain>
   ```

4. Configure a managed-SMTP domain policy with:

   - a domain authentication plan containing the bounce domain, for example
     `returns.<staging-domain>`
   - a DKIM key reference created through
     `/api/v1/domain-delivery-policies/{policy_id}/dkim-key`
   - a managed-SMTP delivery route pointing at this Postfix submission service

   Email Engine uses the bounce domain as the SMTP envelope sender
   (`bounces+<send_record_id>@<bounce-domain>`) and adds
   `X-Email-Engine-DKIM-Selector` / `X-Email-Engine-DKIM-Key-Ref` headers so the MTA-side signer
   can select the correct key without storing private DKIM material in Email Engine metadata.

5. Send only to a low-volume seed list on a staging domain.
6. Post a signed feedback smoke event:

   ```bash
   MANAGED_SMTP_FEEDBACK_SECRET=<secret> \
   BASE_URL=https://<email-engine-api> \
   python scripts/managed_smtp_feedback_smoke.py
   ```

7. Confirm `/api/v1/analytics/overview`, Delivery Manager, and suppressions reflect the feedback.

For the fuller controlled-delivery runbook, use:

```bash
DOMAIN_POLICY_ID=<domain-policy-id> \
CAMPAIGN_ID=<campaign-id> \
SEED_EMAIL=seed@example.com \
MANAGED_SMTP_FEEDBACK_SECRET=<secret> \
BASE_URL=https://<email-engine-api> \
python scripts/managed_smtp_controlled_delivery.py --send-seed --post-feedback
```

The script fails closed on active compliance holds, reputation risk, paused throttles, missing SMTP
diagnostics, and required DNS verification failures unless explicit override flags are supplied for
review-only runs.

## DKIM Signing Boundary

Private DKIM keys should live in the MTA signer or a secret manager, not in Email Engine policy
metadata. The staging Postfix entrypoint supports an optional `POSTFIX_DKIM_MILTER` value, for
example `inet:opendkim:8891`, which configures `smtpd_milters` and `non_smtpd_milters`.

The signer should map `X-Email-Engine-DKIM-Selector` and `X-Email-Engine-DKIM-Key-Ref` to the
actual private key and sign as the policy domain. The existing DKIM key API returns the private key
once for operator storage and keeps only selector, public key, DNS record, and key reference in
policy metadata.

## Bounce Routing Boundary

Email Engine sets the SMTP envelope sender for managed-SMTP records when the domain policy has a
bounce domain. Postfix will emit DSNs to that return path. Production deployments should route the
bounce domain MX back to the managed MTA and feed DSNs or Postfix logs into
`/api/v1/delivery/managed-smtp/feedback`.

To normalize received DSN messages from a bounce-domain mailbox or Maildir:

```bash
MANAGED_SMTP_FEEDBACK_SECRET=<secret> \
BASE_URL=https://<email-engine-api> \
python scripts/managed_smtp_dsn_feedback.py --post \
  --archive-maildir /path/to/archive-Maildir \
  --quarantine-maildir /path/to/quarantine-Maildir \
  /path/to/Maildir
```

Without `--post`, the script prints the normalized feedback payloads for inspection. It maps DSN
`Action: failed` or `5.x.x` status to `dsn_bounce`, `Action: delayed` or `4.x.x` status to
`tempfail`, and successful DSN actions to `delivered`.
When `--quarantine-maildir` or `MANAGED_SMTP_DSN_QUARANTINE` is set, messages that do not produce a
managed-SMTP feedback event are moved out of the inbound Maildir for operator review.

For scheduler wiring, use the combined runbook:

```bash
BASE_URL=https://<email-engine-api> \
MANAGED_SMTP_FEEDBACK_SECRET=<secret> \
MANAGED_SMTP_DSN_PATH=/path/to/Maildir \
MANAGED_SMTP_DSN_ARCHIVE=/path/to/archive-Maildir \
MANAGED_SMTP_DSN_QUARANTINE=/path/to/quarantine-Maildir \
python scripts/managed_smtp_maintenance_runbook.py
```

The runbook calls `/api/v1/domain-delivery-policies/managed-smtp-maintenance`, then posts parsed
DSN feedback when a DSN path is configured. When `MANAGED_SMTP_DSN_ARCHIVE` or `--archive-maildir`
is set, DSN Maildir messages are moved to the archive only after successful feedback posting.
When `MANAGED_SMTP_DSN_QUARANTINE` or `--quarantine-maildir` is set, malformed or non-DSN messages
are moved to the quarantine Maildir without blocking valid DSNs in the same batch.

## MTA Boundary

Postfix handles SMTP transport. Email Engine remains responsible for:

- send job and recipient queue state
- domain route policy
- retry/dead-letter operator controls
- signed feedback ingestion
- suppression creation
- analytics rollups

The first staging feedback path is API-based. DSN parsing and MTA log forwarding both emit the same
signed `ManagedSmtpFeedbackEvent` payloads.

For a first MTA-log bridge, pipe Postfix delivery logs through:

```bash
tail -F /var/log/mail.log \
  | MANAGED_SMTP_FEEDBACK_SECRET=<secret> \
    BASE_URL=https://<email-engine-api> \
    python scripts/managed_smtp_log_feedback.py --post -
```

Without `--post`, the script prints normalized feedback JSON for inspection. It currently maps
Postfix `status=sent` to `delivered`, `status=bounced` to `dsn_bounce`, and `status=deferred` or
`status=expired` to `tempfail`.
