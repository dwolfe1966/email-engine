# Product Backlog

AI enablement is tracked in `docs/AI_ENABLEMENT_PLAN.md`.

## Product Direction

Email Engine is now the primary product surface, not only the backend API. The goal is to turn
`email-engine.app` into a self-standing ESP with a high-quality admin GUI for template building,
audience work, campaign management, delivery operations, tracking, reporting, analytics, and AI
assistance.

SentientMail remains a supported external/admin GUI client, and its strongest UX patterns should be
ported into Email Engine where they improve the native product. New backend/API work should keep the
SentientMail integration contract in mind, but the default implementation target is the native
Email Engine admin unless a task explicitly says otherwise.

This backlog is organized around the target platform capabilities:

1. Mapping and pulling from complex heterogeneous data stores
2. Audience building
3. Campaign management
4. Template development with robust dynamic-template language
5. Journey management
6. Delivery management with work queues
7. Tracking
8. Analytics

## P0: Platform Foundation

- Add production authentication for GUI-to-API requests.
- Add account, user, credential, role, and permission management so users can create credentials and
  be permissioned to specific product areas, API scopes, features, and operational functions.
- Add list response envelopes with `items`, `limit`, `offset`, and `total`.
- Add update/delete endpoints for templates, campaigns, contacts, data sources, and audiences.
- Add a comprehensive activity log that stores every meaningful activity across the service,
  including GUI actions, API calls, background jobs, auth events, imports, template changes,
  campaign operations, delivery actions, tracking events, AI actions, provider callbacks, errors,
  and system/admin changes.
- Add audit logs for admin mutations as a security/compliance view over the broader activity log.
- Add structured JSON logging and request IDs.
- Add release-phase migration automation for the deployment platform.
- Establish Email Engine Admin as the primary ESP GUI with consistent navigation, operation
  feedback, selected-entity highlighting, responsive layouts, and raw/API debug fallbacks.
  **Initial admin pages, navigation, global operation feedback, entity highlighting, and system
  diagnostics shipped.**
- Keep SentientMail compatibility as an integration target, but avoid making SentientMail-only UX or
  API assumptions the source of truth for new Email Engine product work.

## P0.5: Native ESP Admin Experience

The native admin should become as strong as or stronger than the current SentientMail GUI. Near-term
work should focus on reusing the good SentientMail UX patterns while making the Email Engine object
model clearer and more operationally complete.

### Admin-v2 / ESP Workflow Refinement Queue

1. Campaign workspace polish
   - Make campaign create/edit feel like a guided workflow: setup, template/content, audience,
     launch/test send, and results.
   - Improve selected campaign summary, launch readiness messaging, launch progress feedback, and
     post-launch success/failure states.
   - Keep campaign creation as the primary cross-entity workflow tying templates, audiences,
     delivery, and analytics together.
2. Template editor next
   - Improve the template workspace now that the list page is cleaner.
   - Better separate HTML/Jinja editing, WYSIWYG/design, sample variables, preview, CSS helpers, and
     AI assist.
   - Keep render/preview/test-send feedback visible and variable-aware.
3. Audience builder next
   - Keep the audience list page clean while making the detail builder easier to reason about.
   - Improve matched-contact preview, available filter attributes, and rule impact feedback.
   - Make audience selection more campaign-aware.
4. Analytics / Reports
   - Add real charts and trend views for opens, clicks, bounces, unsubscribes, failures,
     deliverability, throughput, and audience/campaign comparison.
   - Keep reports fast by loading lightweight defaults first and progressively fetching heavier
     panels.
5. AI enablement
   - Add template improvement assistant, campaign creation assistant, audience recommendation
     assistant, performance analysis assistant, and always-on workflow assistant.
6. Integration hardening
   - Keep SentientMail aligned to Email Engine API objects and contracts.
   - Document the SentientMail-to-Email Engine workflow contracts.
   - Add cross-app smoke tests for import -> template -> campaign -> test send -> metrics.
   - Reduce fallback and legacy paths once the contracts stabilize.
7. Folder organization
   - Add user-manageable folders for campaigns, templates, and audiences.
   - Support folder CRUD, move/remove actions, folder filters in list pages, and default unfiled
     views.
   - Keep folders as organization metadata, not ownership/security boundaries, unless access control
     requirements are added later.
8. Account and permissions area
   - Add a general account area where account admins can manage users, credentials, API keys, roles,
     permissions, feature access, and operational privileges.
   - Make permissions visible in the GUI and enforce them in API handlers for sensitive operations
     such as imports, launch, provider configuration, AI usage, user management, and data export.
9. Global activity log
   - Add a searchable, filterable activity log UI and API backed by append-only event storage.
   - Capture every significant activity with actor, account, target entity, request ID, before/after
     metadata where appropriate, source surface, result, duration, and error details.
   - Support entity-level activity feeds for campaigns, templates, audiences, contacts, journeys,
     delivery records, account settings, and provider configuration.

### Template Builder / Template Editor

- Make `/template-editor` a full production authoring surface, not only a test tool.
- Improve WYSIWYG fidelity for existing HTML/Jinja templates, including robust source-to-block and
  block-to-source round trips.
- Add stronger Design tab controls for common email layout blocks, buttons, images, tables, trust
  elements, dividers, spacers, and reusable sections.
- Add CSS builder controls for typography, spacing, container width, button style, table style,
  color palettes, and mobile-safe defaults.
- Add native sample-data presets per template category and detected variable type.
- Add variable-aware preview behavior that refreshes sample data when selected templates change.
- Add richer Jinja helper UI for loops, conditionals, fallback values, and nested objects.
- Add version history, compare, rollback, and current-version controls in the native EE editor.
- Add AI-assisted template draft/edit/recommend flows directly in the EE editor, with visible
  progress for long-running AI operations.
  **Initial AI draft/edit/recommend APIs, WYSIWYG blocks, CSS helper, sample-variable refresh, and
  sample template collections shipped.**

### Campaign Manager

- Make `/admin/campaigns` the primary campaign workflow surface for create -> validate -> approve
  -> test send -> launch/process -> monitor.
- Port and improve SentientMail campaign UX patterns: workflow strips, launch result banners,
  progress polling, active send counts, clear success/failure states, and campaign list summaries.
  **Initial summary strip, workflow readiness, AI review, test-send panel, and launch progress
  polling shipped.**
- Add a campaign table/list view with fixed columns, wrapping long content, fast loading, filters,
  search, pagination, status tabs, and progress cells.
- Add clearer launch modes: dry run, test send, scheduled launch, queue launch, process queued.
- Add campaign-level snapshot of template, audience, variables, and approval status used at launch.
- Add explicit campaign event timeline and delivery drilldowns from the campaign page.
- Add campaign examples and starter workflows for ecommerce, subscription, social, SaaS onboarding,
  lifecycle, and reactivation use cases.

### Reports / Analytics

- Make `/admin/analytics` the native reports hub for operators and marketers.
- Port and improve SentientMail reports UX patterns: overview cards, focused campaign panels,
  campaign rate comparison, trend charts, domain/provider deliverability views, event drilldowns,
  and fast filter changes.
  **Initial campaign focused panel, rate comparison, KPI cards, timeline charts, overview, campaign,
  audience, journey, and domain reports shipped.**
- Add time-series graphs for opens, clicks, bounces, unsubscribes, failures, deliverability, and
  campaign throughput.
- Add comparison views for campaigns, audiences, journeys, templates, domains, and providers.
- Add operator-friendly report defaults that load quickly, then progressively fetch heavier panels.
- Add export/download for report tables and chart data.
- Add AI analytics summaries and recommended next actions once metrics stabilize.

## P1: Data Source Mapping And Ingestion

- Add `data_sources` for Postgres, MySQL, Snowflake, BigQuery, REST APIs, CSV/S3, and manual uploads.
- Add `data_source_mappings` to map external fields into canonical contact/profile/event objects.
- Add connection validation endpoints that do not expose credentials.
  **Initial provider-neutral validation endpoint shipped.**
- Add schema discovery endpoints for tables, columns, and sample rows.
  **Initial schema discovery endpoint over config, samples, and mappings shipped.**
- Add ingestion jobs with status, counts, errors, and retry metadata.
- Add normalized profile/contact attribute merge rules.
- Add read-only connector execution with allowlisted queries or parameterized extraction plans.

## P2: Audience Building

- Add `audiences` with rule-tree definitions over contact fields, attributes, events, and imported data.
- Add audience preview endpoints with estimated counts and sample contacts.
- Add materialized audience membership snapshots for repeatable campaign sends.
  **Initial audience snapshot model and endpoints shipped.**
- Add exclusion logic for unsubscribed, suppressed, bounced, complained, and manually excluded contacts.
- Add audience versioning so a campaign can reference the exact audience definition used at send time.
  **Campaign launches with an audience now attach the generated audience snapshot to the send job.**

## P3: Campaign Management

- Add campaign update/delete endpoints and status transitions.
- Add campaign scheduling fields and launch endpoint.
  **Initial `scheduled_at` field and due-campaign processor shipped.**
- Add campaign approval gates and validation checks.
  **Initial validation and approval gate shipped; real launches require approved/scheduled status.**
- Add campaign send summary fields: queued, sent, delivered, opened, clicked, bounced, complained, unsubscribed, failed.
- Add campaign cloning and draft/version workflow.
  **Initial campaign clone endpoint and draft-reset workflow shipped.**

## P4: Template Development

- Add template preview and validation endpoints. **Initial sandboxed preview/validation shipped.**
- Add template variable extraction and required-variable contracts. **Initial undeclared/missing variable extraction shipped.**
- Add template versions with immutable snapshots.
- Add reusable partials/components.
- Add support for robust Jinja2 features with a sandboxed environment. **Initial sandboxed renderer shipped.**
- Add template linting for unsubscribe links, tracking links, missing variables, and unsafe content.
  **Initial lint endpoint shipped for unsubscribe, unsafe HTML, tracking placeholders, and email hygiene.**
- Add approval workflow for production templates.

## P5: Journey Management

- Add `journeys`, `journey_steps`, and `journey_enrollments`.
- Add trigger types: event, audience entry, schedule, API call, and manual enrollment.
- Add delay/wait steps and conditional branches.
  **Initial wait step execution and conditional branch routing shipped.**
- Add suppression and exit rules.
- Add journey run history and per-contact timeline.
- Add journey DAG visualizer for the GUI admin. It should render each journey as a directed graph with node-level state, step type, conditions, wait settings, queued/sent/error counts, and branch/exit paths. Initial frontend research favors React Flow for interactive React node/edge UX, with Dagre for automatic directed layout; Cytoscape.js remains a candidate if deeper graph analysis becomes more important than workflow editing.
  **Initial journey graph API and lightweight admin visualizer shipped.**

## P6: Delivery Management And Work Queues

- Add durable `email_send_records` separate from provider events. **Initial foundation shipped.**
- Add campaign fanout jobs and per-recipient send jobs. **Initial foundation shipped.**
- Add queue backend abstraction, starting with database-backed queues and moving to SQS/RabbitMQ.
- Add worker process for batch rendering and sending. **Initial on-demand processor shipped.**
- Add retry/backoff handling for transient delivery errors.
- Add domain throttling rules and per-provider rate controls.
- Add suppression checks before send.
- Keep provider interfaces neutral so SendGrid, SMTP/Postfix, Mailgun, and future providers can be swapped without changing campaign, audience, template, tracking, or analytics domains.
- Add a dedicated managed-SMTP/reputation platform track. This is a major, high-complexity service
  area that should eventually let Email Engine operate its own outbound SMTP infrastructure using
  mature open-source components such as Haraka, Postal, ZoneMTA, Postfix, or similar tooling rather
  than depending on a paid ESP provider.
- Managed SMTP must include IP pool management, domain onboarding, DKIM/SPF/DMARC setup, bounce and
  complaint processing, warmup plans, rate limits, domain throttles, queue isolation, blocklist
  monitoring, feedback loops, provider-specific retry policy, reputation scoring, abuse controls,
  tenant isolation, and operational dashboards.
- Treat the managed SMTP/reputation system as its own platform subsystem with staged research,
  architecture, operational runbooks, security review, compliance review, and load/reputation testing
  before production use.

## P7: Tracking And Provider Webhooks

- Add SendGrid webhook endpoint with signature verification. **Verifier support shipped; production enforcement requires configuring the SendGrid public key.**
- Add suppression updates for hard bounces, spam complaints, and unsubscribes. **Initial suppression handling shipped.**
- Add provider-neutral webhook/event adapters so SendGrid-specific logic does not leak into the core event, suppression, or analytics models.
- Add open pixel endpoint with signed tracking IDs.
- Add click redirect endpoint with signed tracking IDs.
- Add provider message ID correlation to send records.
- Add event timeline endpoints for contacts, campaigns, and journeys.
  **Initial filterable email event timeline endpoints shipped.**

## P8: Analytics

- Add campaign rollups for sent, delivered, opened, clicked, bounced, complained, unsubscribed, failed, and suppressed counts.
  **Initial campaign performance report endpoint shipped.**
- Add dashboard summary endpoint for the GUI.
  **Initial v1 analytics overview endpoint shipped.**
- Add audience performance reports.
  **Initial audience performance report endpoint shipped.**
- Add journey performance reports by step and branch.
  **Initial journey and step performance report endpoint shipped.**
- Add provider/domain deliverability reports.
  **Initial domain deliverability report endpoint shipped.**
- Add cohort reports by source, segment, and imported data attributes.

## P9: Scale, Operations, And Compliance

- Add staging environment and deployment promotion gates.
- Add dependency/security scanning.
- Add load tests for ingestion, audience preview, campaign fanout, and provider delivery.
- Add OpenTelemetry tracing and metrics.
- Add privacy export/delete workflows.
- Add Terraform/Pulumi for production infrastructure once worker/queue needs outgrow Vercel.
