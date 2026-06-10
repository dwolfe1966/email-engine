# API Integration

Base URL:

```text
/api/v1
```

Interactive OpenAPI docs are available at:

```text
/docs
```

SentientMail campaign workflow examples are available in
`docs/SENTIENTMAIL_CAMPAIGN_EXAMPLES.md`.

## Frontend-Ready Endpoints

Templates:

- `GET /api/v1/templates?limit=100&offset=0`
- `GET /api/v1/templates/list?limit=100&offset=0`
- `POST /api/v1/templates`
- `POST /api/v1/templates/lint`
- `POST /api/v1/templates/preview`
- `POST /api/v1/templates/validate`
- `GET /api/v1/templates/{template_id}`
- `PATCH /api/v1/templates/{template_id}`
- `DELETE /api/v1/templates/{template_id}`

Campaigns:

- `GET /api/v1/campaigns?limit=100&offset=0`
- `GET /api/v1/campaigns/list?limit=100&offset=0`
- `POST /api/v1/campaigns`
- `POST /api/v1/campaigns/process-due?limit=25`
- `GET /api/v1/campaigns/{campaign_id}`
- `PATCH /api/v1/campaigns/{campaign_id}`
- `DELETE /api/v1/campaigns/{campaign_id}`
- `POST /api/v1/campaigns/{campaign_id}/clone`
- `POST /api/v1/campaigns/{campaign_id}/validate`
- `POST /api/v1/campaigns/{campaign_id}/approve`
- `POST /api/v1/campaigns/{campaign_id}/launch`
- `POST /api/v1/campaigns/{campaign_id}/test-preview`
- `POST /api/v1/campaigns/{campaign_id}/test-send`
- `GET /api/v1/campaigns/{campaign_id}/workflow-status`
- `GET /api/v1/campaign-send-jobs/list?campaign_id={campaign_id}`
- `GET /api/v1/email-send-records/list?campaign_id={campaign_id}`
- `POST /api/v1/delivery/process-queued?limit=25&campaign_id={campaign_id}`
- `POST /api/v1/delivery/process-queued?limit=25&send_job_id={send_job_id}`
- `POST /api/v1/provider-webhooks/sendgrid`
- `GET /api/v1/suppressions?limit=100&offset=0`

Contacts:

- `GET /api/v1/audiences/contacts?limit=100&offset=0`
- `GET /api/v1/audiences/contacts/list?limit=100&offset=0`
- `POST /api/v1/audiences/contacts`
- `GET /api/v1/audiences/contacts/{contact_id}`
- `PATCH /api/v1/audiences/contacts/{contact_id}`
- `DELETE /api/v1/audiences/contacts/{contact_id}`
- `POST /api/v1/audiences/contacts/{contact_id}/unsubscribe-token`

Data sources and audiences:

- `GET /api/v1/data-sources?limit=100&offset=0`
- `GET /api/v1/data-sources/list?limit=100&offset=0`
- `POST /api/v1/data-sources`
- `GET /api/v1/data-sources/{data_source_id}`
- `PATCH /api/v1/data-sources/{data_source_id}`
- `DELETE /api/v1/data-sources/{data_source_id}`
- `GET /api/v1/data-source-mappings?limit=100&offset=0`
- `GET /api/v1/data-source-mappings/list?limit=100&offset=0`
- `POST /api/v1/data-source-mappings`
- `PATCH /api/v1/data-source-mappings/{mapping_id}`
- `DELETE /api/v1/data-source-mappings/{mapping_id}`
- `GET /api/v1/audiences?limit=100&offset=0`
- `GET /api/v1/audiences/list?limit=100&offset=0`
- `POST /api/v1/audiences`
- `GET /api/v1/audiences/{audience_id}`
- `PATCH /api/v1/audiences/{audience_id}`
- `DELETE /api/v1/audiences/{audience_id}`
- `POST /api/v1/audiences/preview`

Sending and events:

- `POST /api/v1/emails/send`
- `POST /api/v1/tests/send-email`
- `GET /api/v1/events?limit=100&offset=0`
- `POST /api/v1/events`
- `GET /api/v1/events/{event_id}`
- `GET /api/v1/unsubscribe/{token}`

## Current Integration Notes

- Pagination is offset-based with `limit` capped at 500. Existing list endpoints still return arrays; `/list` variants return `{ "items": [], "limit": 100, "offset": 0, "total": 0 }`.
- CORS is controlled by `CORS_ORIGINS`.
- Authentication is not implemented yet. Put the deployed API behind a private network, gateway, or platform auth until API-key or session authentication is added.
- Email delivery is provider-neutral at the platform boundary. SendGrid is the current production provider; SMTP/Postfix, Mailgun, or another provider should be added behind the provider interface rather than changing campaign, audience, template, event, or analytics contracts.
- Templates use a sandboxed Jinja2 renderer with `StrictUndefined`. Supported language features include variables, filters, loops, conditionals, macro syntax, and Jinja expressions. Validation extracts undeclared variables and reports missing variables before send. Linting checks unsubscribe presence, unsafe HTML, tracking placeholders, plain-text fallback, long subjects, and image alt text. Reusable partial storage and richer lint rules are still backlog items.
- `POST /api/v1/emails/send` sends to an existing contact using an existing template. The render context includes contact fields, contact `attributes`, flattened contact attributes, and request `variables`; request variables win on key conflicts.
- `POST /api/v1/campaigns/{campaign_id}/validate` checks template variables, audience match count, suppression count, and queued count.
- `POST /api/v1/campaigns/{campaign_id}/approve` moves a valid campaign to `scheduled`; non-dry-run launches require this gate.
- Campaigns have optional `scheduled_at`; approve accepts `scheduled_at`, and `POST /api/v1/campaigns/process-due` queues approved campaigns whose scheduled time has arrived.
- `POST /api/v1/campaigns/{campaign_id}/clone` creates a draft copy of a campaign. Editing campaign content resets its status to `draft`; use approve rather than PATCH to enter `scheduled`.
- `POST /api/v1/campaigns/{campaign_id}/launch` creates durable campaign send jobs and queued send records. Dry runs remain allowed before approval.
- `POST /api/v1/delivery/process-queued` is an operator endpoint that processes queued send records through the configured provider. Use `campaign_id` or `send_job_id` to target a specific queued campaign/job. It is a bridge toward a true worker/scheduler process.
- `POST /api/v1/domain-delivery-policies/{policy_id}/authentication-plan` generates and stores
  managed-SMTP DNS onboarding instructions for a domain policy, including DKIM, SPF, DMARC,
  bounce-domain MX, staging MTA MX, and staging MTA A-record placeholders.
- `POST /api/v1/domain-delivery-policies/{policy_id}/dkim-key` generates a DKIM keypair for the
  domain policy. The private key is returned once and only the key reference, public key, and DNS
  record are stored in policy metadata.
- `POST /api/v1/domain-delivery-policies/{policy_id}/verify-authentication` checks the stored DNS
  onboarding plan against DNS when the runtime has `dig`; unavailable lookups return `unchecked`
  records rather than silently passing.
- `POST /api/v1/domain-delivery-policies/{policy_id}/blocklist-scan` checks configured or supplied
  sending IPv4 addresses against DNSBL zones, then stores `blocklist_status`, `blocklist_hits`,
  `blocklist_checked_at`, and `ip_addresses` in domain policy metadata when requested.
- `GET /api/v1/domain-delivery-policies/{policy_id}/reputation-dashboard` combines domain policy
  warmup/throttle/IP-pool metadata, authentication verification state, and domain deliverability
  rollups into one managed-SMTP readiness view. The response also surfaces active compliance holds,
  blocklist preflight state, sending IP addresses, and warmup progression status when present.
- `POST /api/v1/domain-delivery-policies/{policy_id}/warmup-progress` evaluates current domain
  deliverability against warmup thresholds, then advances, holds, waits, or keeps the warmup stage
  while recording audit metadata.
- `POST /api/v1/domain-delivery-policies/managed-smtp-maintenance` is the scheduler-friendly batch
  entrypoint for managed-SMTP policies. It can run blocklist scans and warmup progression across
  policies, returning per-domain results for cron/operator logs.
- `POST /api/v1/domain-delivery-policies/{policy_id}/compliance-hold` pauses a domain policy for
  operator abuse/compliance review and appends a hold entry to policy metadata audit history.
- `POST /api/v1/domain-delivery-policies/{policy_id}/release-compliance-hold` clears the active
  compliance hold, resumes domain policy claiming, and appends a release entry to the audit history.
- `POST /api/v1/provider-webhooks/sendgrid` ingests SendGrid delivery, bounce, complaint, and unsubscribe events. Bounce, dropped, spam report, and unsubscribe events create suppression records that block future sends.
- SendGrid Event Webhook signature verification is supported through `SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY`. Set `SENDGRID_EVENT_WEBHOOK_REQUIRE_SIGNATURE=true` in production after the public key is configured.
- `POST /api/v1/delivery/managed-smtp/feedback` ingests owned-MTA feedback events such as
  `delivered`, `dsn_bounce`, `feedback_loop_complaint`, `unsubscribe`, and `tempfail`. Feedback
  events are retained in `provider_feedback_events` with provider/source idempotency keys; duplicate
  events are reported through `duplicate_count` and skipped before send-record mutation.
  Configure `MANAGED_SMTP_FEEDBACK_SECRET`; callers sign
  `{X-Email-Engine-Timestamp}.{raw_body}` with HMAC-SHA256 and send the hex digest in
  `X-Email-Engine-Signature`. Requests outside
  `MANAGED_SMTP_FEEDBACK_SIGNATURE_TOLERANCE_SECONDS` are rejected.
- `POST /api/v1/tests/send-email` renders an existing template with provided variables and sends to an arbitrary email address for manual testing.
- Legacy aliases `POST /api/v1/send/contact` and `POST /api/v1/send/test` still work, but they are hidden from OpenAPI and should not be used by new clients.
- Unsubscribe links should use tokens generated by `POST /api/v1/audiences/contacts/{contact_id}/unsubscribe-token`.

## Example Requests

Create a template:

```json
{
  "name": "welcome",
  "subject": "Welcome {{ first_name }}",
  "html_body": "<p>Hello {{ first_name }}</p>",
  "text_body": "Hello {{ first_name }}"
}
```

Upsert a contact:

```json
{
  "email": "person@example.com",
  "first_name": "Person",
  "last_name": "Example",
  "source": "web_app",
  "attributes": {
    "plan": "trial"
  }
}
```

Send a test:

```json
{
  "template_id": "00000000-0000-0000-0000-000000000000",
  "to_email": "person@example.com",
  "variables": {
    "first_name": "Person"
  }
}
```

Send to an existing contact:

```json
{
  "template_id": "00000000-0000-0000-0000-000000000000",
  "contact_id": "00000000-0000-0000-0000-000000000000",
  "campaign_id": null,
  "variables": {
    "first_name": "Person"
  }
}
```
