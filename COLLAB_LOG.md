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
