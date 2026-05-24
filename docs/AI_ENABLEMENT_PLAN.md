# AI Enablement Plan

## Direction

AI should be an assistive layer over the existing Email Engine objects, not a replacement for the
campaign, template, audience, delivery, or analytics contracts. The core platform should stay
provider-neutral so OpenAI, local models, or future providers can sit behind the same internal
service interface.

## First AI Surfaces

### 1. Template Builder Agent

Purpose:

- Turn a natural-language brief into a Jinja template draft.
- Generate subject, HTML, text fallback, and CSS.
- Use existing native variables: `tracking_open`, `tracking_click`, `tracking_click_base`,
  `unsubscribe_url`.
- Return detected variables and sample data for preview.

Initial API shape:

```http
POST /api/v1/ai/templates/draft
```

Request:

```json
{
  "brief": "Create a trial activation email for SaaS users.",
  "brand": {
    "name": "SentientMail",
    "primary_color": "#2563eb",
    "tone": "direct, helpful"
  },
  "required_variables": ["first_name", "plan", "recommendations"]
}
```

Response:

```json
{
  "subject": "...",
  "html_body": "...",
  "css_body": "...",
  "text_body": "...",
  "sample_variables": {},
  "notes": []
}
```

### 2. Content Creator Agent

Purpose:

- Generate campaign copy variations.
- Produce subject line alternatives.
- Rewrite copy for tone, clarity, length, or segment.
- Keep output compatible with existing Jinja variable constraints.

Initial API shape:

```http
POST /api/v1/ai/content/variants
```

### 3. Audience Selection Assistant

Purpose:

- Explain available contact attributes.
- Suggest audience `rule_tree` definitions from a natural-language segment request.
- Preview the impact before saving.

Initial API shape:

```http
POST /api/v1/ai/audiences/rule-tree
```

Request:

```json
{
  "prompt": "Trial users at SaaS companies who have not clicked in the last 30 days.",
  "available_fields": ["source", "attributes.plan", "attributes.company", "attributes.last_click_at"]
}
```

Response:

```json
{
  "rule_tree": {
    "operator": "and",
    "rules": []
  },
  "explanation": "..."
}
```

### 4. Performance Analyst Agent

Purpose:

- Summarize campaign analytics.
- Identify deliverability or engagement risks.
- Recommend next actions such as subject rewrite, resend segment, suppression review, or timing
  change.

Initial API shape:

```http
POST /api/v1/ai/analytics/summary
```

### 5. Workflow Assistant Agent

Purpose:

- Sit beside the admin workflow.
- Read workflow status, template variables, audience preview, and analytics.
- Explain blockers and recommend the next operation.
- Never send, approve, or delete without an explicit user action.

Initial API shape:

```http
POST /api/v1/ai/workflow/next-action
```

## Internal Architecture

Add an AI provider abstraction:

```text
email_platform/providers/ai.py
```

Core concepts:

- `AIMessage`
- `AIRequest`
- `AIResponse`
- `AIProvider`
- `build_ai_provider(settings)`

Settings:

- `AI_PROVIDER=disabled|openai|local`
- `AI_MODEL`
- `AI_API_KEY`
- `AI_TIMEOUT_SECONDS`

The default should be `disabled`. Admin pages can show AI controls only when AI is configured.

## Safety And Control

- AI endpoints draft and recommend; they do not directly send email.
- Generated templates must run through existing lint, variable detection, preview, and validation.
- Audience rule suggestions must run through audience preview before save.
- Analytics recommendations should include the underlying metrics used.
- Store prompt, response, model, and linked entity IDs in an `ai_runs` table for auditability.
- Do not include SMTP credentials, provider secrets, API keys, or private deployment config in AI
  prompts.

## Proposed Backlog

1. Add provider-neutral AI settings and disabled provider.
2. Add `ai_runs` table for audit records.
3. Implement `/api/v1/ai/templates/draft` with a deterministic disabled/mock mode for tests.
4. Add Template Editor panel: brief input, generate draft, preview, save as template.
5. Implement `/api/v1/ai/audiences/rule-tree` using known contact fields.
6. Add Audience Builder assistant: prompt to rule tree, preview, save.
7. Implement `/api/v1/ai/analytics/summary`.
8. Add Campaign/Analytics assistant panel with recommended next actions.
9. Add workflow assistant using `/api/v1/campaigns/{campaign_id}/workflow-status`.
10. Add provider implementations, starting with OpenAI behind the provider interface.

## Near-Term Slice

The best first implementation slice is a mockable Template Builder Agent:

- It produces a draft template from a brief.
- It always includes unsubscribe and tracking placeholders.
- It immediately runs existing template variable inspection and linting.
- It appears in the Template Editor as a side panel.
- It can be tested without real model credentials.
