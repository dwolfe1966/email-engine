# ESP Project Status

Date: 2026-06-01
Branch: `codex/weekend-platform-work`

## Current State

Email Engine has moved beyond a backend scaffold and is now the primary native ESP product surface.
The native admin GUI is the main implementation target for template building, audience work,
campaign management, delivery operations, tracking, analytics, and AI assistance. SentientMail
remains a supported external client and a useful source of UX patterns, but new product work should
default to Email Engine's own admin and API model.

Recent work has focused heavily on the template editor and design workflow. The latest commits added
or refined resizable design panes, canvas zoom, selected-block breadcrumbs, nested-block parent
navigation, live-canvas ancestor highlights, column resize/move/duplicate controls, mobile column
behavior, autosaved local drafts, and version-history restore from the editor.

The platform also has meaningful shipped foundations across:

- Native admin navigation and operational pages.
- Template preview, validation, linting, version snapshots, sample variables, and sandboxed Jinja
  rendering.
- AI draft, edit, recommendation, campaign review, audience review, delivery review, journey review,
  and analytics-review endpoints.
- Campaign validation, approval, clone, launch, test-send, due-campaign processing, workflow
  readiness, and launch-progress polling.
- Audience CRUD, CSV preview/import, contacts, metadata, preview, and audience snapshots.
- Delivery queues, send records, requeue/skip actions, tracking links, opens/clicks, unsubscribe,
  suppressions, provider webhooks, and analytics surfaces.
- Data-source validation, schema discovery, mappings, and import-job records.
- Dual auth mount for both `/api/v1/auth/*` and `/api/auth/*`, keeping the shared SentientMail UI
  compatible with Email Engine.
- Production `REQUIRE_GUI_AUTH` enforcement for operator `/api/v1` routes while keeping auth,
  tracking open/click, unsubscribe, visitor demo access, and SendGrid webhook endpoints publicly
  callable.

## Working Tree

Tracked files are currently clean. The repo has untracked local material that should stay out of
normal commits unless deliberately reviewed and sanitized:

- ESP research/design PDF and visual-design PNGs.
- SendGrid/OpenAI/Twilio local reference files that appear sensitive.
- CSV test/audience data files.

## Product Direction

The roadmap should continue treating Email Engine as a full ESP platform, not a demo console. The
highest-value direction is hardening the native operational product while keeping compatibility with
SentientMail where contracts are already shared.

Near-term priorities remain:

1. Continue Admin-v2 workflow polish across campaigns, overview, templates, audiences, analytics,
   journeys, delivery, suppressions, and data sources.
2. Account, role, permission, credential, and API-key management.
3. Global activity and audit logging for GUI actions, API calls, background jobs, auth events,
   imports, template changes, campaign operations, delivery actions, tracking events, AI actions,
   provider callbacks, errors, and admin changes.
4. Consistent list envelopes, update/delete coverage, request IDs, structured logging, and deploy
   migration automation.
5. Folder organization for campaigns, templates, and audiences.

## Immediate Engineering Note

Auth infrastructure and `/api/v1` route classification are active in production behind
`REQUIRE_GUI_AUTH=true`. The guard protects operator API traffic while exempting auth, tracking
pixels/click redirects, unsubscribe, visitor demo access, and provider webhooks. Visitor access is
read-oriented and blocks user-management API access.
