# Collab log

Running record of cross-repo changes between **email-engine** (this
repo) and **SentientMail** (`daxym76/SentientMail` — the React UI +
the SpokeoESP demo backend).

Maintained primarily by Chris's Claude instance, but David's Claude is
welcome (encouraged) to append entries too — the goal is that whichever
side picks the work up next has a single place to read what just landed
elsewhere and what they need to do about it.

Newest entries first. Each entry should answer four questions:

1. **What changed** — files, endpoints, contracts.
2. **Why** — design rationale or what audit finding it addresses.
3. **What the other side needs to do** — migrations to run, configs
   to set, contract decisions to make.
4. **Compatibility notes** — breaking changes, deprecations, anything
   that requires coordination before merging in either direction.

---

## 2026-06-09 — Provider-neutral delivery feedback ingestion

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added `DeliveryFeedback` as the normalized feedback item contract for provider and managed-SMTP
  delivery outcomes.
- Added `FeedbackIngestionService` to persist normalized feedback as email events, send-record
  lifecycle status updates, and suppressions.
- Refactored SendGrid webhook ingestion so SendGrid only normalizes payloads, then delegates
  persistence to the shared feedback service.
- Existing `/api/v1/provider-webhooks/sendgrid` response counts stay compatible.

### Why

Managed SMTP needs to feed DSNs, bounce mailbox parsing, feedback-loop complaints, and MTA logs
through the same persistence path as third-party provider webhooks.

### What needs to happen next

- Add a managed-SMTP feedback ingestion contract that converts DSN/bounce/complaint/MTA log inputs
  into `DeliveryFeedback`.
- Decide which feedback inputs are synchronous API payloads, background-polled mailboxes, or
  append-only MTA log streams.

### Compatibility notes

- SendGrid webhook API shape is unchanged; only internal normalization and persistence ownership
  moved.

---

## 2026-06-09 — Delivery lifecycle status expansion

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added send-record lifecycle statuses for `submitted`, `deferred`, `delivered`, `bounced`,
  `complained`, and `unsubscribed`.
- Delivery processing now records accepted adapter submissions as `submitted` and retryable
  failures as `deferred`.
- Provider feedback events now promote records into delivered, bounced, complained, or unsubscribed
  lifecycle states.
- Analytics, send-job progress, overview, and Delivery Manager counts roll richer lifecycle states
  into existing queue, accepted, failed, and suppression buckets.
- Added Alembic revision `0020_send_lifecycle_statuses`.

### Why

Managed SMTP needs a durable lifecycle that separates adapter acceptance from final inbox outcome
and keeps transient deferrals distinct from records that have never been attempted.

### What needs to happen next

- Normalize SendGrid webhook handling behind a provider-neutral feedback service so managed SMTP,
  SendGrid, and future adapters emit the same feedback contract.
- Add managed-SMTP feedback ingestion for DSNs, bounce mailbox events, complaints, and MTA logs.

### Compatibility notes

- Public counters remain backward compatible by folding `deferred` into queued, `submitted` and
  `delivered` into sent/accepted, `bounced` into failed, and complaints/unsubscribes into
  suppression review.

---

## 2026-06-09 — Delivery Manager audit surfacing

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Delivery Manager now surfaces `claim_blocked` and `dead_lettered` delivery-attempt audit rows.
- Added React ESP admin action to load attempt audit rows filtered by selected send record or send
  job.
- Added React ESP admin action to dead-letter the selected send record.
- Added a Delivery Attempt Audit panel showing reason, route, recipient domain, record ID, and
  domain policy reference.
- Static `/admin/delivery` also gained Dead-letter Record and Load Attempt Audit actions.

### Why

The send engine now persists queue-control and dead-letter audit rows. Operators need those rows
visible in Delivery Manager so policy pauses, throttles, and terminal queue decisions are
explainable.

### What needs to happen next

- Expand send statuses and transition logic.
- Normalize SendGrid webhooks through a provider-neutral feedback service.
- Continue toward managed-SMTP feedback ingestion and the deeper `DeliveryAdapter` boundary.

### Compatibility notes

- No API or schema changes in this slice.
- Rebuilt `frontend/dist` assets are included.

---

## 2026-06-09 — Dead-letter queue controls

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added terminal `dead_lettered` send-record status.
- Added `POST /api/v1/email-send-records/{send_record_id}/dead-letter` for operator terminal
  queue control.
- Dead-lettering writes a `delivery_attempts` audit row with route type `queue_control`, route key
  `dead_lettered`, previous status, and operator reason.
- Send-job progress now includes `dead_lettered_count` and treats dead-lettered records as
  processed.
- Requeue remains available for dead-lettered records that need recovery.

### Why

Operators need a terminal state for records that should not keep cycling through retries or remain
ambiguously failed. This creates the first explicit terminal queue-control path before broader
delivery lifecycle expansion.

### What needs to happen next

- Surface claim-blocked and dead-letter audit rows in Delivery Manager.
- Expand send statuses and transition logic.
- Continue toward provider-neutral feedback ingestion and the deeper `DeliveryAdapter` boundary.

### Compatibility notes

- Adds Alembic revision `0019_dead_letter_send_status`.
- Existing delivery behavior is unchanged unless an operator explicitly dead-letters a record.
- PostgreSQL enum downgrade leaves the value in place because enum values cannot be dropped safely
  without type recreation.

---

## 2026-06-09 — Queue-control audit persistence

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Delivery queue claiming now persists a `delivery_attempts` audit row when a queued record is not
  claimed because of domain policy controls.
- Audit rows use status `claim_blocked`, route type `queue_control`, and route key equal to the
  block reason such as `domain_policy_paused`, `domain_policy_max_per_minute`, or
  `domain_policy_max_concurrent`.
- `DeliveryRunRead` now includes skipped count and skipped record IDs.
- Throttle counters now count only actual submission attempts (`submitting`/`submitted`) so audit
  rows do not extend throttle windows.

### Why

Delivery Manager and future AI/operator workflows need an explainable record of why queued sends
were not claimed. This makes domain throttles and pauses inspectable instead of invisible.

### What needs to happen next

- Add Delivery Manager UI surfacing for `claim_blocked` rows.
- Add dead-letter state and explicit terminal queue controls.
- Continue expanding send lifecycle states before the deeper `DeliveryAdapter` implementation.

### Compatibility notes

- No migration in this slice; it reuses `delivery_attempts`.
- Existing records remain queued when blocked by policy controls.
- Existing delivery behavior remains unchanged for domains without a policy.

---

## 2026-06-09 — Domain queue-control enforcement

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added explicit pause/resume shortcut APIs for delivery routes and domain delivery policies.
- Delivery queue claiming now consults domain delivery policies before moving records from
  `queued` to `sending`.
- Paused domain policies, `max_per_minute`, and `max_concurrent` limits prevent records from being
  claimed while leaving them queued for later processing.
- Claiming accounts for records reserved in the current batch so one process run does not exceed a
  low per-domain cap.

### Why

Domain policies are now active queue-control inputs, not only planning metadata. This is required
before managed SMTP warmup, domain throttling, route failover, and emergency pause workflows can be
trusted operationally.

### What needs to happen next

- Add persisted throttle/skip audit events so Delivery Manager can explain why queued records were
  not claimed.
- Add dead-letter states and terminal queue controls.
- Continue expanding send lifecycle states before the deeper `DeliveryAdapter` implementation.

### Compatibility notes

- No migration in this slice; it uses the existing delivery route and domain policy tables.
- Existing records remain queued when blocked by policy controls.
- Existing delivery behavior remains unchanged for domains without a policy.

---

## 2026-06-09 — Domain delivery policy foundation

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added domain delivery policies as the third managed SMTP/send-engine foundation slice.
- Domain policies store exact recipient domain, preferred delivery route, throttle hints,
  warmup stage, pause window, and metadata.
- Route selection now prefers a matching non-paused domain policy route before falling back to
  active provider routes or `EMAIL_PROVIDER`.
- Delivery attempts now include domain policy ID, warmup stage, and throttle hint metadata when a
  policy drives selection.

### Why

This is the first control-plane layer needed for provider/MTA routing by recipient domain,
managed-SMTP warmup, domain-specific throttling, and emergency domain pause controls.

### What needs to happen next

- Enforce domain policy throttle hints in queue claiming and processing.
- Add explicit pause/resume shortcuts for routes and domain policies.
- Then continue toward the deeper `DeliveryAdapter` boundary so route-selected providers execute
  from route config instead of only global settings.

### Compatibility notes

- Existing delivery behavior remains compatible because policy selection falls back to route/default
  settings when no matching policy exists or a policy is paused.
- Adds Alembic revision `0018_domain_delivery_policies`.
- Adds operator APIs under `/api/v1/domain-delivery-policies`.

---

## 2026-06-09 — Delivery routes foundation

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Added first-class delivery routes as the next managed SMTP/send-engine foundation slice.
- Delivery routes model the future provider/MTA route layer with route type, status, priority,
  config, secret reference, and metadata.
- Added route selection for delivery processing. For now it prefers an active route matching the
  configured `EMAIL_PROVIDER` and falls back to settings when no route exists.
- Delivery attempts now record selected route type/key/source metadata.

### Why

This creates the control-plane table needed before managed SMTP, domain policies, fallback routes,
warmup, and provider/MTA failover can become real operator workflows.

### What needs to happen next

- Add domain delivery policies for per-domain route selection, throttles, warmup stages, and pause
  windows.
- Then introduce the deeper `DeliveryAdapter` boundary so route-selected providers can execute from
  route config instead of only global settings.

### Compatibility notes

- Existing delivery behavior remains compatible because route selection falls back to
  `EMAIL_PROVIDER`.
- Adds Alembic revision `0017_delivery_routes`.
- Adds operator APIs under `/api/v1/delivery-routes`.

---

## 2026-06-09 — Explicit managed SMTP direction

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Product direction clarified: one foundation item is to build, deploy, and operate an Email
  Engine-managed SMTP server and reputation layer rather than depending on paid relays such as
  SendGrid or Amazon SES as the primary delivery architecture.
- Added `docs/MANAGED_SMTP_SEND_ENGINE_PLAN.md` with current foundation, target architecture,
  lifecycle states, data-model tasks, service/API tasks, MTA deployment track, and the first
  implementation slice.

### Why

The next SMTP/send-engine foundation work should assume first-party SMTP ownership is a core
platform objective. Third-party providers can remain useful adapters, migration paths, or fallback
routes, but they should not define the long-term delivery model.

### What needs to happen next

- Walk the owned SMTP/send-engine foundation task from architecture through first implementation
  slice: queue model, provider/MTA boundary, retry policy, bounce and complaint ingestion,
  deliverability telemetry, and operator controls.
- Start the first code slice by adding a `DeliveryAttempt` model/read schema and teaching
  `DeliveryService.process_queued` to persist one attempt per provider submission.

### Compatibility notes

- Adds a new `delivery_attempts` table through Alembic revision `0016_delivery_attempts`.
- Adds a new operator API: `GET /api/v1/delivery-attempts/list`.
- Existing send-record APIs and provider behavior remain compatible.

---

## 2026-06-08 — ESP platform-readiness UI pass and current handoff

**Pushed by:** Codex
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- Template Editor polish landed before this handoff:
  - one collapsible `Template Controls` preflight container above the workspace,
  - workspace module tabs moved above status messages,
  - status messages default open,
  - hidden Feedback pane can be restored with a global `+ Feedback` row.
- A platform-foundation documentation pass was added across the ESP admin UI. Recent pushed commits include:
  - `9913ada` Docs API lifecycle readiness panel
  - `c4a9f94` Integrations connector roadmap
  - `92938c8` Data connector sync contract
  - `3eca8ad` Delivery send-engine operations contract
  - `81f454a` Compliance feedback policy contract
  - `f8f4cf2` Analytics deliverability signal contract
  - `d025aef` AI workflow agent contract
  - `909dbff` Settings platform governance contract
  - `edbf9b7` Contacts relationship contract
  - `27652c5` Audience segmentation contract

### Why

David raised that major foundations are still missing even while UI polish is improving: data connectors across RDBMS/warehouse/NoSQL/API sources, multi-entity joins, client-owned entities, owned SMTP server, send queues, bounce queues, deliverability feedback, and ever-present AI agents. The recent pass makes those gaps visible in the operator UI instead of hiding them in backlog notes.

### What needs to happen next

Recommended next backlog slice: move from UI readiness panels into implementation planning for one foundation area. The best next candidate is the **owned SMTP/send engine** because Delivery, Compliance, Analytics, Integrations, Docs, Settings, and Overview now all point at the same gap.

Practical next steps:

1. Draft backend implementation plan for owned SMTP server, MTA policy, send queues, retry policy, bounce classification, complaint handling, and feedback ingestion.
2. Decide whether the first implementation target is internal queue tables/APIs, SMTP submission/MTA integration, or bounce/complaint event ingestion.
3. Convert the chosen foundation into schema/API tasks and tests before adding more UI panels.

### Compatibility notes

- No known breaking API changes in this pass; most changes are React UI copy/panels, CSS, tests, and rebuilt `frontend/dist` assets.
- Repeated verification pattern was:
  - `npm run build`
  - focused frontend workflow test for the touched page
  - `.venv/bin/pytest tests/test_api_contract.py`
- Existing untracked local files were intentionally left untouched:
  - `docs/ESP Research and Design.pdf`
  - `docs/OpenAI API Key.rtf`
  - `docs/SendGrid.rtf`
  - `docs/twilio_2FA_recovery_code.txt`
  - `docs/visual-design-*.png`
  - `tests/Milkbar_Email_List_6_4_.xlsx - subs*.csv`
  - `tests/random_people_100.csv`

---

## 2026-05-25 (later 2) — Auth router mounted under BOTH `/api/v1/auth/*` and `/api/auth/*`

**Pushed by:** Chris's Claude
**Repo touched:** `dwolfe1966/email-engine` only.

### What changed

- `src/email_platform/api/auth.py` — `APIRouter` declaration no
  longer carries `prefix='/api/v1/auth'`. The handlers still
  declare paths as `/login`, `/logout`, `/me` relative to whatever
  prefix the mount supplies.
- `src/email_platform/main.py` — `include_router(auth_router)`
  now happens twice:

  ```python
  app.include_router(auth_router, prefix='/api/v1/auth')
  app.include_router(auth_router, prefix='/api/auth')
  ```

  Both prefixes share one set of handlers, one schema, one DB read.

### Why

The shared SentientMail React UI in `daxym76/SentientMail/ui/`
hardcodes `/api/auth/login` (no `/v1`). David's Vercel
deployment of that UI talks to email-engine, which used to mount
auth only at `/api/v1/auth/login`. Result: every login attempt
on `ui-eight-rho.vercel.app` returned 404 → UI fell back to
the generic "Invalid email or password" message → looked like a
credentials problem when it was actually a routing problem.

This is the "Option A" of the two paths called out in the prior
COLLAB_LOG entry (the other being a UI-side `VITE_AUTH_BASE`
env). Option A wins on:
- Cheaper to ship (no UI rebuild, no Vercel env coordination).
- Lower-blast-radius (additive — David's existing `/v1` clients
  untouched).
- Future-proof if the API path conventions ever diverge —
  the shared UI keeps one path; backend-specific clients keep
  their `/v1` namespace.

### What the SentientMail side needs to do

Nothing. The shared UI was already calling `/api/auth/...`; this
makes that call succeed on David's deployment too.

### Compatibility notes

- **Backward-compatible.** Anyone hitting `/api/v1/auth/login` on
  email-engine still hits the same handler, same response.
- **Routing-only change.** No handler logic touched, no schema
  changed, no DB migration. `pytest` clean (19 passing).
- **Cookie scope unchanged.** Same `esp_session` name, same
  HttpOnly/Secure/SameSite=Lax shape, same Max-Age.
- **No effect on email-engine's other routers** (admin_console,
  template_editor, etc.) — auth is still the only router with
  this dual-mount.
- **Future cleanup:** if email-engine ever decides to retire the
  `/v1` prefix on auth (or move it to `/v2`), the dual-mount
  makes that a one-line change.

---

## 2026-05-25 (later) — Spokeo side: nginx basic-auth dropped + `require_user` enforced on all non-auth/non-health routes

**Pushed by:** Chris's Claude
**Repos touched:** `daxym76/SentientMail` only. email-engine
unchanged this round, but worth knowing about so the contract
expectations don't drift.

### What changed (Spokeo backend, for context)

- The nginx basic-auth wall in front of `esp.cpew.me` is gone.
  App-level cookie auth is now the only gate.
- Every router except `health` and `auth` mounts with
  `dependencies=[Depends(require_user)]`. Anonymous calls return
  401 with `WWW-Authenticate: Cookie`.

### Why email-engine should care

When you're ready to do the equivalent move on email-engine
(drop whatever fronting layer protects it — Vercel auth /
Cloudflare access / etc. — and rely on app-level cookies),
mirror the pattern:

```python
from fastapi import Depends
from email_platform.services.auth import require_user  # to be written

protected = [Depends(require_user)]
app.include_router(router, dependencies=protected)
app.include_router(compat_router, dependencies=protected)
app.include_router(admin_console_router, dependencies=protected)
app.include_router(test_console_router, dependencies=protected)
app.include_router(template_editor_router, dependencies=protected)

# Stay public:
app.include_router(auth_router)
# (health endpoint is at app-level, also public)
```

### What needs to happen first on this side

`require_user` doesn't exist in `services/auth.py` yet — only the
service-layer primitives. Add a FastAPI `Depends` helper, mirror
of our spokeo `auth.py:optional_user / require_user`:

```python
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session
from email_platform.db.session import get_db
from email_platform.models.entities import User
from email_platform.services.auth import SESSION_COOKIE_NAME, lookup_session

def optional_user(
    db: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> User | None:
    if not token:
        return None
    row = lookup_session(db, token)
    if row is None:
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    db.commit()
    return user

def require_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user
```

Drop that in `services/auth.py` (or a new `api/deps.py` if you
prefer to keep services/ free of FastAPI imports — our Spokeo
side has it co-located in `auth.py` for now).

### Compatibility notes

- No contract change visible to the UI on either side. Cookie
  shape is identical; only the gating layer moved from
  nginx → app.
- If you have an in-flight workstream that depends on
  unauthenticated access to email-engine endpoints from outside
  the GUI (e.g. a tester / curl-from-CI flow), it'll need a
  session cookie or an API-key alternative (separate workstream,
  not in scope today).

---

## 2026-05-25 — App-level auth on both backends + shared `<LoginCanvas>` UI

**Pushed by:** Chris's Claude
**Repos touched:** `daxym76/SentientMail` (commits `b10cb99` + merge
`94cf3cc`), `dwolfe1966/email-engine` (commit `2831995c`).

### What changed in email-engine (this repo)

- `User` + `UserSession` ORM models added to `models/entities.py`,
  matching the existing `PGUUID` / `Mapped` / `StrEnum` style.
- `services/auth.py` — argon2id hashing, session token mint/hash/
  lookup/revoke, sliding-expiry refresh, lockout helpers, and the
  `authenticate()` entry point used by the route.
- `api/auth.py` — `POST /api/v1/auth/login`,
  `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`. Mounted in
  `main.py` before the other routers so it appears first in OpenAPI.
- Alembic migration `0015_users_and_sessions` creates the `users` and
  `user_sessions` tables.
- `scripts/seed_user.py` — admin CLI to seed the first operator.
- `argon2-cffi` added to `pyproject.toml` and `requirements.txt`.

### What changed in SentientMail (`daxym76/SentientMail`)

- Shared React UI: new `/login` route outside the shell
  (`ui/src/canvas/LoginCanvas.tsx`), new `AuthProvider` context
  (`ui/src/state/authContext.tsx`), new `<ProtectedRoute>` wrapping
  everything else (`ui/src/components/ProtectedRoute.tsx`), new auth
  API wrappers in `ui/src/lib/api.ts` (`authLogin`, `authLogout`,
  `authMe`, `apiFetch`, `AuthError`). TopNav shows signed-in email +
  Sign-out button.
- SpokeoESP backend (`src/spokeo_esp/`) got the same auth scaffold
  as email-engine but at `/api/auth/...` (no `/v1` prefix) and
  CORS narrowed from `allow_origins=["*"]` to a per-env allowlist.

### Auth contract (shared between both backends)

```
POST /api/v1/auth/login       (this backend)
POST /api/auth/login          (SpokeoESP backend)
  body: { email: string, password: string }
  resp: { user: { id, email, display_name, role } }
  side effect: Set-Cookie: esp_session=<32-byte token>; HttpOnly;
               Secure (non-local); SameSite=Lax; Max-Age=2592000; Path=/

POST /api/v1/auth/logout      (this backend)
POST /api/auth/logout         (SpokeoESP backend)
  resp: 204 No Content
  side effect: Set-Cookie: esp_session=; Max-Age=0
  Idempotent — repeated calls with no/expired cookie still 204.

GET  /api/v1/auth/me          (this backend)
GET  /api/auth/me             (SpokeoESP backend)
  resp: { user: { id, email, display_name, role } } | 401
```

- **Password storage:** argon2id (library defaults), stored in
  `users.password_hash`. Plaintext never logged or written to disk.
- **Cookie token:** 32-byte URL-safe random (`secrets.token_urlsafe(32)`).
  Only `sha256(token)` is stored in the DB so a read-only DB compromise
  doesn't grant active sessions.
- **Lockout:** 5 failed attempts → account locked for 30 minutes. State
  on the user row (`failed_login_count` + `locked_until`); resets on
  successful login or operator password reset.
- **Sliding expiry:** every authenticated request bumps `last_seen_at`;
  when remaining time < 7 days, `expires_at` extends by another 30.
- **Constant-time decoy:** the "no such user" branch runs an argon2
  verify against a stable decoy hash so login response timing doesn't
  leak account existence.

### What needs to happen next on email-engine

1. **Run the migration** against the deployed Postgres:
   ```
   alembic upgrade head
   ```
2. **Seed the first user** (replace email/password):
   ```
   python scripts/seed_user.py --email you@domain --password '<strong-secret>'
   ```
3. **Decide the UI ⇄ email-engine path mapping.** The shared UI today
   calls `/api/auth/login` etc. (no `/v1`). Two options when wiring
   the UI against email-engine:
   - **(A)** Add a no-prefix alias mount on email-engine —
     `app.include_router(auth_router, prefix='')` or a second router
     that mirrors the `/v1` paths under `/api/auth/...`.
   - **(B)** Add a build-time `VITE_AUTH_BASE` env to the UI
     (default `/api/auth`) so the SentientMail build sets it to
     `/api/v1/auth` and the SpokeoESP build leaves the default.
   - Recommendation: **B**. It's the future-correct shape since
     other API paths will diverge too. ~10-line change in
     `ui/src/lib/api.ts`.
4. **Apply auth to existing mutating routes** when you're ready to
   make auth mandatory. The auth endpoints are exposed but existing
   routes (`/api/v1/templates/...`, `/api/v1/campaigns/...`, etc.)
   are still unauthenticated, intentionally, so demos aren't broken
   mid-rollout. A FastAPI `Depends()` on a `require_user` factory
   would do it — happy to write that side too if you want me to
   take that part.

### Compatibility notes

- **No breaking changes** to existing endpoints. Auth is additive.
- The `users` and `user_sessions` table names use plural snake_case
  consistent with everything else in `entities.py`. The Python class
  is `User` and `UserSession` (User is singular — `UserSession`
  avoids confusion with the SQLAlchemy `Session` and the existing
  `CampaignSendJob` naming pattern).
- `argon2-cffi` is the only new dep. It compiles a small C extension
  at install — no runtime fetches. Wheels are published for all the
  Python versions email-engine targets.

---

## How to add a new entry

When you push anything cross-cutting (UI contract changes, schema
changes, security fixes, new endpoints the other side would want to
mirror, env vars, deploy changes), add a new entry at the TOP of
this file with today's date.

Brief is fine — the goal is "what does the other side need to know"
not "what did I do today." Skip the entry if it's purely local to
one repo and doesn't affect the other.
