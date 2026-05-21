# SentientMail GUI Review and Email-Engine Overlap

Reviewed repository: `https://github.com/daxym76/SentientMail`  
Reviewed checkout: `/private/tmp/SentientMail` at commit `c548d0e` on `main`  
Comparison target: local `email-engine` repository, current working tree

## Executive Summary

`SentientMail` is not only a GUI admin. It is a full prototype product: FastAPI backend, Postgres schema, simulator, AI authoring layer, approvals, reports, and a Vite/React admin UI. The local `email-engine` repo is a much smaller provider-neutral sending backend. They overlap conceptually around templates, contacts/audiences, campaigns/sends, events, and unsubscribe/compliance, but their API contracts do not line up yet.

The fastest integration path is to treat `email-engine` as the production sending core and adapt or shim the SentientMail UI API calls. Directly pointing the current SentientMail UI at `email-engine` will not work because the UI calls `/api/...` endpoints and expects richer shapes than `email-engine` currently exposes under `/api/v1/...`.

## Code Review Findings

### High: API has no application-level auth

SentientMail currently relies on deployment-level basic auth according to the README, while the FastAPI app itself registers all routers without auth dependencies. The CORS middleware is also configured wide open with credentials enabled.

Evidence:

- `SentientMail/src/spokeo_esp/api/__init__.py:38-44` sets `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`, and `allow_credentials=True`.
- `SentientMail/README.md:82-84` says the production-shape demo is basic-auth gated at nginx.
- `SentientMail/src/spokeo_esp/api/routes/chat.py:129-131` exposes the LLM chat endpoint without an auth dependency.

Impact:

If this backend is deployed outside a tightly controlled reverse proxy, any reachable caller can list contacts, create sends, launch sends, call AI endpoints, and inspect providers. Before using it as the admin GUI for a production sending backend, add API-key/session auth and tenant resolution from the authenticated principal.

### High: Tenant selection is hardcoded to Spokeo

Most backend routes call `_spokeo_tenant_id()`, which looks up `Tenant.slug == "spokeo"` on every request.

Evidence:

- `SentientMail/src/spokeo_esp/api/routes/journeys.py:17-23`
- Used across templates, contacts, segments, sends, approvals, reports, experiments, assets, and AI routes.

Impact:

This blocks general SentientMail use and makes integration with `email-engine` ambiguous. `email-engine` currently has no tenant model, while SentientMail assumes all domain data is tenant-scoped. Decide whether the combined product is single-tenant for MVP or introduce tenant/account IDs in `email-engine` before binding the GUI to it.

### High: GUI endpoint contract does not match email-engine

The SentientMail UI hardcodes relative `/api/...` paths and response envelopes. `email-engine` exposes `/api/v1/...` and simpler response bodies.

Evidence:

- SentientMail UI calls `fetch("/api/templates")` and expects `{ items: [...] }`: `SentientMail/ui/src/lib/api.ts:100-104`.
- SentientMail UI calls `fetch("/api/chat")`: `SentientMail/ui/src/sse.ts:49-54`.
- `email-engine` templates are under `/api/v1/templates` and return a plain list for `GET`: `src/email_platform/api/routes.py:37-43`.
- `email-engine` has no `/api/chat`, `/api/segments`, `/api/sends`, `/api/approvals`, `/api/reports`, or `/api/templates/{id}/versions`.

Impact:

The GUI cannot be integrated by only changing a base URL. It needs either an adapter layer that implements the SentientMail `/api` contract on top of `email-engine`, or a frontend rewrite to consume `email-engine`’s `/api/v1` contract.

### Medium: Approval workflow is advisory, not enforced

SentientMail exposes an approvals canvas, but launches are allowed without approval.

Evidence:

- `SentientMail/src/spokeo_esp/api/routes/approvals.py:3-7` says launching without approval is allowed.
- `SentientMail/src/spokeo_esp/api/routes/sends.py:218-247` launches a send after status validation, without checking approval state.

Impact:

For a marketing/email admin, this is risky because the UI can imply governance that the backend does not enforce. If approvals remain in the GUI, launch endpoints should require an approved approval row or a deliberate override permission.

### Medium: Dependency audit has unresolved moderate vulnerabilities

Verification:

- `npm ci` succeeded in `SentientMail/ui`.
- `npm run build` succeeded.
- `npm audit --json` reported 4 moderate vulnerabilities.

Notable packages:

- `vite` from `ui/package.json:26`
- `@monaco-editor/react` from `ui/package.json:13`, through `monaco-editor` and `dompurify`

Impact:

The Vite/esbuild items are mostly dev-server exposure risks, but this admin tool edits and previews HTML, so the DOMPurify chain deserves attention before production use.

### Medium: Preview iframe allows forms and popups in untrusted email HTML

The preview pane renders template HTML through `srcDoc` with a sandbox that permits forms and popups.

Evidence:

- `SentientMail/ui/src/components/compose/PreviewPane.tsx:35-49`

Impact:

Scripts are not allowed, and `allow-same-origin` is omitted, which is good. Still, admin-authored or AI-authored email HTML can open popups and submit forms from the preview. For a production admin, consider a stricter preview mode by default and an explicit "interactive preview" mode only when needed.

### Low: Runtime docs disagree on backend port

The root README says the API runs on `:8090` locally, while the UI README and Vite config default the proxy to `localhost:8000`.

Evidence:

- `SentientMail/README.md:75` uses FastAPI on `:8090`.
- `SentientMail/ui/README.md:14-20` says the backend defaults to `localhost:8000`.
- `SentientMail/ui/vite.config.ts:7` defaults `API_TARGET` to `http://localhost:8000`.

Impact:

This creates avoidable setup failures. Pick one default port or document `API_TARGET=http://localhost:8090 npm run dev`.

## SentientMail Strengths to Reuse

- Richer admin concepts than `email-engine`: template versions, structured `document_json`, segment builder, send lifecycle, approvals, reports, AI draft workflow, and provider manifest.
- Server-side template validation before persistence.
- Contact PII masking in data and segment preview endpoints.
- Row locking around several state-changing send and approval operations.
- Production-shaped static UI serving from FastAPI when `ui/dist` exists.

## Overlap: Domain Model

| Area | SentientMail | email-engine | Fit |
| --- | --- | --- | --- |
| Templates | `Template` plus `TemplateVersion`, current version, `document_json`, validation, AI draft | `EmailTemplate` with `name`, `subject`, `html_body`, `text_body` | Conceptual overlap, contract mismatch |
| Contacts | Tenant-scoped contacts with regulated/intent/consent fields, PII masking | Global contacts with email/name/source/attributes/unsubscribe | Partial overlap |
| Audiences | `Segment` definitions with rules, preview, cached estimated size | `Campaign.audience_query` only; no segment endpoints | Missing in `email-engine` |
| Sends/Campaigns | `Send` object with draft/scheduled/sent states and metrics | `Campaign` object with draft/scheduled/sending/sent/paused, but no send launch/fanout | Partial overlap |
| Events | Rich event model and reporting queries | `EmailEvent` with contact/campaign/provider/message metadata | Good conceptual overlap |
| Providers | AI providers plus simulated sends; SES planned | Console, SendGrid, SMTP email providers | Complementary |
| Compliance | FCRA validator, suppressions, approvals, masked data | Unsubscribe flag and signed unsubscribe token | Complementary, SentientMail richer |
| Auth/Tenants | Hardcoded Spokeo tenant; no app auth | No auth or tenant model | Both need production work |

## Endpoint Contract Comparison

| GUI call in SentientMail | Current expectation | email-engine equivalent | Gap |
| --- | --- | --- | --- |
| `GET /api/templates` | `{ items: TemplateSummary[] }` with current version summary | `GET /api/v1/templates` returns `TemplateRead[]` | Path and shape mismatch |
| `GET /api/templates/{id}` | Template detail with `versions[]` | `GET /api/v1/templates/{id}` returns one flat template | Missing versions |
| `POST /api/templates/{id}/versions` | Create version, validate, maybe set current | None | Missing |
| `POST /api/render` | Render preview with merge slots | None | Missing |
| `POST /api/render-document` | Compile block document to HTML | None | Missing |
| `POST /api/templates/{id}/ai-draft` | AI draft endpoint | None | Missing |
| `GET /api/providers` | AI provider manifest | None | Missing |
| `GET /api/segments` | `{ items: SegmentSummary[] }` | None | Missing |
| `POST /api/segments/preview` | Audience preview | None | Missing |
| `GET /api/contacts` | Paginated `{ total, limit, offset, items }` with filters | `GET /api/v1/audiences/contacts` returns `ContactRead[]` | Path, filters, envelope mismatch |
| `GET /api/sends` | `{ items: SendDetail[] }` | `GET /api/v1/campaigns` partially maps | Semantics mismatch |
| `POST /api/sends/{id}/launch` | Resolve recipients, simulate/send, return metrics | None; only `POST /api/v1/send/test` | Missing production send lifecycle |
| `GET /api/events` | Not directly used by GUI; reports query events | `GET /api/v1/events` | Backend overlap |
| `GET /api/reports/overview` | Dashboard rollups | None | Missing |
| `GET /api/approvals` | Approval queue | None | Missing |
| `POST /api/chat` | SSE agent chat | None | Missing |

## Recommended Integration Strategy

### Phase 1: Keep email-engine as the sending core

Implement a compatibility API in `email-engine` under `/api` or update the GUI to use a configurable API base and `/api/v1`. A compatibility API is lower-risk because the GUI already has many calls and shapes.

Minimum compatibility endpoints for first usable GUI:

- `GET /api/templates`
- `GET /api/templates/{id}`
- `POST /api/templates/{id}/versions` or map saves to flat template update/create
- `GET /api/contacts`
- `GET /api/contacts/_meta`
- `GET /api/sends`
- `POST /api/sends`
- `POST /api/sends/{id}/launch`
- `GET /api/reports/overview`

### Phase 2: Decide which richer SentientMail backend concepts to port

The GUI assumes product concepts that do not exist in `email-engine`: segments, sends, reports, approvals, template versions, and AI drafting. Port these deliberately instead of bending the GUI into the current simple `Campaign` model.

Recommended additions to `email-engine`:

- `TemplateVersion` table and endpoints.
- `Segment` table and audience preview endpoints.
- `Send` table separate from `Campaign`.
- `Suppression` table for unsubscribe/bounce/complaint handling.
- Provider webhook endpoint for SendGrid.
- Dashboard/reporting endpoints over events.
- Auth and tenant/account context.

### Phase 3: Frontend configuration cleanup

In SentientMail UI:

- Add a central `API_BASE_URL` helper instead of raw `fetch("/api/...")` calls.
- Keep request/response types generated from OpenAPI once `email-engine` stabilizes.
- Align dev proxy docs and defaults to the chosen backend port.
- Add auth header/cookie handling in the shared API wrapper.

## Deployment Readiness Comparison

SentientMail:

- Frontend build works with Node 24 and locked dependencies.
- Static serving exists when `ui/dist` is present.
- Backend requires Python 3.11; this shell only had Python 3.9, so backend tests were not run.
- App-level auth is missing; relies on nginx/basic auth.
- CORS is wide open in code.

email-engine:

- Has Dockerfile and deployment docs in current working tree.
- Has provider abstraction for real email sending via console, SendGrid, or SMTP.
- Has simpler OpenAPI surface under `/api/v1`.
- Needs auth, provider webhooks, real campaign/send lifecycle, and richer reporting before it can fully back the SentientMail GUI.

## Verification Performed

SentientMail frontend:

```bash
cd /private/tmp/SentientMail/ui
npm ci
npm run build
npm audit --json
```

Results:

- `npm ci`: passed.
- `npm run build`: passed.
- `npm audit --json`: failed with 4 moderate vulnerabilities.

SentientMail backend:

- Not run. The repository requires Python `>=3.11`, but the available interpreter in this shell was Python `3.9.6`.

email-engine:

- Earlier `pytest`, `ruff`, and `mypy` commands were unavailable because the local Python dev environment is not installed in this shell.

## Bottom Line

Do not try to wire the current SentientMail GUI directly to `email-engine` without a contract layer. The overlap is real, but SentientMail is a richer prototype backend plus UI, while `email-engine` is a lean sending service scaffold. The practical path is:

1. Deploy `email-engine` as the production API core.
2. Add a compatibility `/api` layer or update the GUI through a shared API client.
3. Port SentientMail concepts into `email-engine` in this order: auth, template versions, segments, sends, provider webhooks, reports, approvals, AI drafting.
