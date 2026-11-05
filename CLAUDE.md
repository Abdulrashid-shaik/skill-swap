# CLAUDE.md — SkillSwap

SkillSwap is a non-monetary peer-to-peer skill exchange platform. **The `docs/` directory is the source of truth.** Read it before working; keep it current as you build.

## Read first
- [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) — vision, the 10 absolute rules, locked stack
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — apps, config, request flow
- [docs/DATABASE_ERD.md](docs/DATABASE_ERD.md) — entities, constraints, delete behavior
- [docs/BUSINESS_RULES.md](docs/BUSINESS_RULES.md) — matching, state machines, **dual confirmation**
- [docs/API_DESIGN.md](docs/API_DESIGN.md) — `/api/v1/` conventions
- [docs/UI_DESIGN_SYSTEM.md](docs/UI_DESIGN_SYSTEM.md) — Sky-Blue design system, pages, voice
- [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) — phases + acceptance criteria
- [docs/REQUIREMENTS_TRACEABILITY.md](docs/REQUIREMENTS_TRACEABILITY.md) — requirement → phase → signal
- [docs/DECISIONS.md](docs/DECISIONS.md) — ADRs + decision log R1–R17

## Absolute rules (never violate)
Non-monetary; no payments/credits/points/subscriptions; **no AI features or AI branding**; no public feed; no custom video system; Google Meet only via Google Calendar; no fake data; no unnecessary tech. Do not implement anything that contradicts the requirements without asking first.

## Locked stack
Python 3.12+, Django 5.2 LTS, DRF, Django ORM · Django Templates + vanilla JS + Fetch · **SQLite only** · session auth + CSRF. **Forbidden:** React/Angular/Vue/Next, Node/npm builds, Redis, Celery, mandatory WebSockets, microservices, external DB. No new dependency without explaining it and getting approval.

## How to work
- **One module at a time**, in roadmap order. Do not advance until the current phase's acceptance criteria pass (tests **and** manual verification). A rendered page is not "done."
- Per module: explain purpose → requirements → dependencies → DB changes → endpoints → UI → security/edge cases → acceptance criteria → implement in small steps → write tests → run tests → manual verify → review for bugs/security → update docs → summarize → recommend a commit message.
- **Enforce all business rules server-side.** Never trust the frontend (especially dual confirmation).
- Custom `User` model from P2 (email login). Keep secrets in env; `.env` gitignored, `.env.example` placeholders only. Google tokens never serialized/logged.
- Inspect existing code before editing. Do not change Git config/remotes or delete repository files without approval. Inner `skill-swap/` repo is canonical.
- Keep docs updated as the source of truth; do not copy the full brief into every file. Do not create skills/subagents/hooks/MCP unless they give a clear, approved benefit.

## Status
**Phases 0–12 built; P13–P15 implemented (DRF API live, deployment docs, hardening).**
Apps: common, accounts, skills, discovery, moderation, notifications, exchanges,
messaging, scheduling, reviews, integrations. **148 tests passing**; `manage.py
check` and `check --deploy` clean.

**Production-hardening pass (see docs/DECISIONS.md build deviations D-E…D-J):**
- **Rate limiting** — atomic DB-backed fixed-window limiter (`apps/common/ratelimit.py`)
  on login, registration, password-reset, chat send, report submit; trusted-proxy-aware
  client IP; 429 + `Retry-After`. Deliberately not `cache.incr()` (non-atomic).
- **Suspension** fully enforced — auth backend (login) + `SuspensionMiddleware`
  (existing sessions) + DRF permission + service guards; `suspended_until` auto-expiry
  is lazy (no scheduler). Staff exempt.
- **One ONGOING exchange per user** (R15) — DB-level `OngoingExchangeParticipant`
  unique(user) + `transaction_mode=IMMEDIATE`; race-safe on SQLite.
- **Logging** — app/security/error streams; secrets/PII never logged.
- **Errors** — branded 400/403/404/405/429/500 (JSON for `/api/`); standalone 500.
- **DRF API** at `/api/v1/` — focused core over the service layer (no logic dup).

- Full loop works: register → skills → **mutual match** → request → accept →
  exchange workspace → **dual-confirm completion** → chat → sessions → review;
  plus notifications, blocking/reporting, admin moderation + skill approval.
- **Deferred/external:** email verification (needs SMTP, R7); Google Calendar/Meet
  (feature-flagged OFF — needs OAuth creds + Google libs, R6/R8).
- See `docs/DECISIONS.md` → Build deviations (template-first vs DRF; inlined CSS/JS
  for the dev proxy; Playwright dev-only).
- Dependencies: `Django`, `djangorestframework`, `Pillow`. Run `pip install -r
  requirements.txt` then `manage.py migrate`.
