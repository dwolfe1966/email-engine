# SentientMail Campaign Integration Examples

Base URL:

```text
https://email-engine.app
```

These examples use the canonical Email Engine `/api/v1` contract. SentientMail can call these
directly or map them behind its existing send/campaign UI.

## Object Mapping

| SentientMail concept | Email Engine object |
| --- | --- |
| Template / version | `EmailTemplate` and `EmailTemplateVersion` |
| Contact | `Contact` |
| Segment / audience | `Audience` with `rule_tree` |
| Send / campaign | `Campaign` |
| Launch/test-send | `CampaignSendJob` and `EmailSendRecord` |
| Reports | `CampaignAnalyticsRead`, events, timelines |

## Create Or Select A Template

```http
POST /api/v1/templates
Content-Type: application/json
```

```json
{
  "name": "welcome-trial",
  "subject": "Hello {{ first_name }}",
  "html_body": "<p>Hello {{ first_name }}</p>{% if plan == \"trial\" %}<p>Your trial is active.</p>{% endif %}<p><a href=\"{{ tracking_click }}\">Open dashboard</a></p>{{ tracking_open }}<p><a href=\"{{ unsubscribe_url }}\">Unsubscribe</a></p>",
  "css_body": "body { font-family: Arial, sans-serif; color: #17202a; }",
  "text_body": "Hello {{ first_name }}. Unsubscribe: {{ unsubscribe_url }}"
}
```

Useful companion endpoints:

- `POST /api/v1/templates/variables`
- `POST /api/v1/templates/preview`
- `POST /api/v1/templates/validate`
- `GET /api/v1/templates/{template_id}/variables`

## Upsert A Contact

```http
POST /api/v1/audiences/contacts
Content-Type: application/json
```

```json
{
  "email": "person@example.com",
  "first_name": "Person",
  "last_name": "Example",
  "source": "sentientmail",
  "attributes": {
    "plan": "trial",
    "company": "Example Co",
    "lifecycle_stage": "lead"
  }
}
```

## Create An Audience

```http
POST /api/v1/audiences
Content-Type: application/json
```

```json
{
  "name": "Trial leads",
  "description": "Contacts currently on a trial plan.",
  "rule_tree": {
    "operator": "and",
    "rules": [
      { "field": "source", "comparator": "eq", "value": "sentientmail" },
      { "field": "attributes.plan", "comparator": "eq", "value": "trial" }
    ]
  }
}
```

Preview the audience before campaign creation:

```http
POST /api/v1/audiences/preview
Content-Type: application/json
```

```json
{
  "rule_tree": {
    "field": "attributes.plan",
    "comparator": "eq",
    "value": "trial"
  },
  "limit": 25
}
```

## Create A Campaign

```http
POST /api/v1/campaigns
Content-Type: application/json
```

```json
{
  "name": "Trial activation campaign",
  "template_id": "00000000-0000-0000-0000-000000000000",
  "audience_query": {
    "field": "attributes.plan",
    "comparator": "eq",
    "value": "trial"
  }
}
```

Before enabling send controls in SentientMail, call workflow status:

```http
GET /api/v1/campaigns/{campaign_id}/workflow-status
```

This returns campaign, template, detected variables, validation, audience preview, analytics,
latest send job, and latest send record in one response.

## Preview And Test Send

Preview the campaign render:

```http
POST /api/v1/campaigns/{campaign_id}/test-preview
Content-Type: application/json
```

```json
{
  "variables": {
    "first_name": "Person",
    "plan": "trial"
  }
}
```

Send one actual test email:

```http
POST /api/v1/campaigns/{campaign_id}/test-send
Content-Type: application/json
```

```json
{
  "to_email": "qa@example.com",
  "variables": {
    "first_name": "QA",
    "plan": "trial"
  }
}
```

The response includes `send_job_id`, `send_record_id`, provider details, rendered bodies, tracking
links, and unsubscribe URL. SentientMail should store or display these IDs for debugging.

## Test Tracking And Metrics

For manual QA, synthetic tracking endpoints are available:

```http
POST /api/v1/tests/email-send-records/{send_record_id}/open
POST /api/v1/tests/email-send-records/{send_record_id}/click?target_url=https%3A%2F%2Fexample.com
```

Fetch campaign metrics:

```http
GET /api/v1/campaigns/{campaign_id}/analytics?send_job_id={send_job_id}
GET /api/v1/campaigns/{campaign_id}/analytics/timeline?send_job_id={send_job_id}&days=30
GET /api/v1/events/list?send_record_id={send_record_id}
```

## Production Smoke Script

Use this as an executable contract example:

```bash
CONTACT_EMAIL=qa@example.com scripts/production_campaign_smoke.py
```

The script creates a full campaign workflow, sends one actual test email, records open/click test
events, and asserts sent/open/click analytics.
