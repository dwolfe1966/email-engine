# Managed SMTP Production Hardening

This runbook is the minimum host and MTA checklist before using the managed-SMTP scaffold for
production delivery. It assumes Email Engine remains the queue, policy, feedback, and operator
control plane while Postfix/OpenDKIM run on a dedicated MTA host.

## Network Boundary

- Allow inbound TCP `25` only from the public internet for remote MX delivery.
- Allow inbound TCP `587` only from trusted Email Engine workers or private network ranges listed in
  `POSTFIX_MYNETWORKS`.
- Do not expose OpenDKIM port `8891` publicly. It should bind to localhost or the internal Docker
  network only.
- Restrict SSH to operator VPN, bastion, or provider console access.
- Keep `smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination` enforced.

## TLS And Identity

- Provision a real certificate for `POSTFIX_MYHOSTNAME`, ideally through the host secret manager or
  certificate automation.
- Mount the certificate at `POSTFIX_TLS_DIR` and set `POSTFIX_TLS_CERT_FILE` /
  `POSTFIX_TLS_KEY_FILE` so Postfix can advertise STARTTLS on SMTP/submission.
- Set DNS `A`, `PTR`, SPF, DKIM, DMARC, and bounce-domain MX records before production warmup.
- Verify each domain policy through `/api/v1/domain-delivery-policies/{policy_id}/verify-authentication`
  before enabling real traffic.
- Rotate DKIM selectors by adding the new DNS record, mounting the new private key, updating
  `OPENDKIM_SELECTOR`, then retiring the old selector after the longest message lifetime has passed.

## Key And Secret Custody

- Store DKIM private keys outside the repository under `OPENDKIM_KEYS_DIR`.
- Enforce owner-only permissions on private keys, for example `0400`.
- Keep `MANAGED_SMTP_FEEDBACK_SECRET` in the scheduler/API secret store and rotate it with a
  maintenance window because DSN and log feedback workers depend on it.
- Do not put private DKIM keys in `DomainDeliveryPolicy.metadata_json`; Email Engine stores only key
  references, public DNS material, and signer hints.

## Queue And Mailbox Retention

- Keep Postfix queue lifetime conservative during warmup; the scaffold defaults to one day.
- Back up or snapshot `POSTFIX_SPOOL_DIR` before MTA host maintenance.
- Mount DSN inbound, archive, and quarantine Maildirs on durable host storage through
  `MANAGED_SMTP_DSN_MAILDIR`, `MANAGED_SMTP_DSN_ARCHIVE_DIR`, and
  `MANAGED_SMTP_DSN_QUARANTINE_DIR`.
- Run the DSN ingestion scheduler with `MANAGED_SMTP_DSN_ARCHIVE` and
  `MANAGED_SMTP_DSN_QUARANTINE` so processed and malformed messages leave the inbound mailbox.
- Run `scripts/managed_smtp_dsn_quarantine.py --check` from cron and alert on non-zero exits.

## Logs And Feedback

- Persist `/var/log/mail.log` or container logs to durable storage through `POSTFIX_LOG_DIR`.
- Forward Postfix delivery logs through `scripts/managed_smtp_log_feedback.py --post` or ingest DSNs
  through `scripts/managed_smtp_dsn_feedback.py --post`.
- Keep retained provider feedback available through `/api/v1/provider-feedback-events/list` for
  incident review.
- Ensure log retention covers the longest support and compliance investigation window.

## Abuse Controls

- Start with low warmup limits and a seed list before customer traffic.
- Run blocklist maintenance and warmup progression daily.
- Use compliance hold APIs to pause domains when complaint, bounce, or blocklist risk appears.
- Keep an operator runbook for emergency domain pause, route pause, and provider fallback.

## Backup And Recovery

- Back up `OPENDKIM_KEYS_DIR`, Postfix queue state, Maildir archive/quarantine paths, and deployment
  environment files.
- Store key backups encrypted and access-limited.
- Test restore by starting the production compose stack with restored keys and confirming OpenDKIM
  can build KeyTable and SigningTable.
- Keep a rollback path to external provider routes while managed-SMTP warmup and reputation are
  still maturing.

## Preflight

Before raising production volume:

1. DNS authentication verification passes.
2. Reputation dashboard is clear.
3. No active compliance hold exists.
4. Blocklist scan has no hits.
5. DSN ingestion, quarantine check, and log feedback jobs are running.
6. Provider feedback evidence UI shows retained MTA feedback events after seed sends.
7. Emergency pause/resume procedures are tested by an operator.
