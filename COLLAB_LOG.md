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
