# API Integration

Base URL:

```text
/api/v1
```

Interactive OpenAPI docs are available at:

```text
/docs
```

## Frontend-Ready Endpoints

Templates:

- `GET /api/v1/templates?limit=100&offset=0`
- `GET /api/v1/templates/list?limit=100&offset=0`
- `POST /api/v1/templates`
- `POST /api/v1/templates/preview`
- `POST /api/v1/templates/validate`
- `GET /api/v1/templates/{template_id}`
- `PATCH /api/v1/templates/{template_id}`
- `DELETE /api/v1/templates/{template_id}`

Campaigns:

- `GET /api/v1/campaigns?limit=100&offset=0`
- `GET /api/v1/campaigns/list?limit=100&offset=0`
- `POST /api/v1/campaigns`
- `GET /api/v1/campaigns/{campaign_id}`
- `PATCH /api/v1/campaigns/{campaign_id}`
- `DELETE /api/v1/campaigns/{campaign_id}`
- `POST /api/v1/campaigns/{campaign_id}/launch`
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
- Templates use a sandboxed Jinja2 renderer with `StrictUndefined`. Supported language features include variables, filters, loops, conditionals, macro syntax, and Jinja expressions. Validation extracts undeclared variables and reports missing variables before send. Approval workflows, reusable partial storage, and richer lint rules are still backlog items.
- `POST /api/v1/emails/send` sends to an existing contact using an existing template. The render context includes contact fields, contact `attributes`, flattened contact attributes, and request `variables`; request variables win on key conflicts.
- `POST /api/v1/campaigns/{campaign_id}/launch` creates durable campaign send jobs and queued send records.
- `POST /api/v1/delivery/process-queued` is an operator endpoint that processes queued send records through the configured provider. Use `campaign_id` or `send_job_id` to target a specific queued campaign/job. It is a bridge toward a true worker/scheduler process.
- `POST /api/v1/provider-webhooks/sendgrid` ingests SendGrid delivery, bounce, complaint, and unsubscribe events. Bounce, dropped, spam report, and unsubscribe events create suppression records that block future sends.
- SendGrid Event Webhook signature verification is supported through `SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY`. Set `SENDGRID_EVENT_WEBHOOK_REQUIRE_SIGNATURE=true` in production after the public key is configured.
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
