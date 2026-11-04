# Decisions

Two parts: **Architecture Decision Records** (the enduring "why") and the **Decision Log R1–R17** (resolved questions with their consequences). Update this file when a decision changes; do not silently alter business rules.

## Architecture Decision Records

### ADR-1 — Custom User model from the start
Define `accounts.User` in P2 with `USERNAME_FIELD="email"` and optional `username`. Changing `AUTH_USER_MODEL` after data exists forces a painful migration. **Consequence:** custom `UserManager`; email unique+indexed.

### ADR-2 — Dual confirmation via confirmation rows + atomic derivation
Completion is derived from `ExchangeConfirmation` rows (`unique(exchange, user)`) inside `transaction.atomic()`, never from the frontend and never by the first row alone. **Consequence:** race-safe on SQLite without row locks (see BUSINESS_RULES §4).

### ADR-3 — Matching computed on demand
No match store/queue. Matching is an ORM query re-validated at request-create and accept. **Consequence:** simple, correct, no Redis; acceptable at expected scale. If scale demands it later, add a denormalized cache table — not now.

### ADR-4 — One `UserSkill` table with a `kind` enum
OFFER/WANT in one table rather than two. **Consequence:** symmetric match queries, less code.

### ADR-5 — Session auth + DRF SessionAuthentication + CSRF
No JWT/tokens/Redis. Template-first app with same-origin JSON endpoints. **Consequence:** object-level permissions guard every exchange-scoped resource.

### ADR-6 — Notifications by `type` + `target_url`
No GenericForeignKey. **Consequence:** simpler schema and queries; deep links instead of generic relations.

### ADR-7 — Google integration isolated and feature-flagged
All Google code lives in `integrations`; the app runs fully without it. **Consequence:** P1–P8 have zero Google dependency; P9 is the only externally-gated phase.

### ADR-8 — SQLite WAL + short atomic writes
Enable WAL; keep write transactions short; rely on `atomic()` + unique constraints for correctness (SQLite serializes writes; `select_for_update` is a no-op). **Consequence:** confirm/accept/review paths are concurrency-safe.

### ADR-9 — No dependencies without approval
`requirements.txt` stays minimal. Candidate installs are explained and approved per phase: Pillow (P2), a token-encryption library (P9). `django-filter` avoided (R10).

## Decision Log (R1–R17)

| # | Decision | Resolution | Consequence | Blocks? |
|---|---|---|---|---|
| R1 | Nested vs outer Git repo | Inner `skill-swap/` is canonical (has the intended remote). Recommend removing the empty outer `workspace/.git`; **do not auto-delete** — confirm first. | Clean single repo | No |
| R2 | Login identity | Email is `USERNAME_FIELD`; username optional display handle. | Custom UserManager | No |
| R3 | User-suggested skills | Users suggest → admin approval before canonical. | `Skill.status` enum + `suggested_by` | No |
| R4 | Notification linking | `type` + `target_url`, no GenericForeignKey. | Simpler schema | No |
| R5 | Block during existing exchange | Existing exchanges stay intact; block affects discovery + new requests only. | See R17 | No |
| R6 | Google token encryption | Encrypt tokens at rest; library choice needs approval in P9. | Isolated to P9 | P9 only |
| R7 | Email verification / reset | Needs company SMTP. If unavailable: defer email-verify; dev-only console backend for reset. | Email features conditional | No |
| R8 | Google credentials | External prerequisite; never invented. | P9 gated | P9 only |
| R9 | Django 5.2 vs env | 5.2 LTS needs Python ≥3.10 — compatible with observed 3.12.3. Confirm installable in company env at P1. | Verify at P1 | Verify |
| R10 | Filtering | DRF/ORM query params; no `django-filter` unless approved. | Hand-rolled filtering | No |
| R11 | "Upcoming session" reminders (no Celery/Redis) | v1: notify at schedule time + compute "upcoming" live on dashboard. True timed reminders only if OS **cron + management command** is permitted. | No broker; timed pushes need cron approval | No |
| R12 | Account suspension | `User.is_suspended` + optional `suspended_until`. Manual unsuspend always works; auto-expiry needs the R11 scheduler. | New User fields | No |
| R13 | Skill approval states | `Skill.status` enum `PENDING/APPROVED/REJECTED`. | Supports rejection/audit | No (P3) |
| R14 | Avatar images | Install **Pillow** (approve P2) for image validation/resize; else degrade to non-image file. | One dependency | Avatar only |
| R15 | Multiple exchanges per pair | Allow many over time; guard against >1 concurrent `ONGOING` for the same participant+skill pair. | Prevents duplicate active exchanges | No |
| R16 | Exchange skill scope | One agreed skill-pair per exchange for v1. | Simpler lifecycle; multi-skill deferred | No |
| R17 | Blocking + intact exchange | Existing exchange fully usable (chat/sessions continue); block only affects discovery + new requests. | Consistent with R5 | No |

## Build deviations (flagged, not silent)

These differ from the original plan; recorded here for review.

- **D-A — Interactive endpoints are template-first + plain-Django JSON, not DRF.**
  Pages are server-rendered Django templates; the one polling surface (chat) uses plain
  `JsonResponse` endpoints (`apps/messaging/views.py`), not DRF viewets. DRF is installed
  and `/api/v1/` is reserved, but the interactive operations were built the template-first
  way (simpler, same session-auth + CSRF guarantees). **If a formal DRF `/api/v1/` surface
  is required, it can be layered on without changing the models/services.**
- **D-B — CSS and chat JS are inlined into the HTML** (`apps/common/templatetags/assets.py`
  and an inline `<script>` in the chat template) instead of linked from `/static/`. This was
  required because the dev-access proxy does not forward `/static/` asset requests. Source
  files under `static/` remain the source of truth; production can switch back to linked
  static files where `/static/` is served normally.
- **D-C — Playwright + Chromium** were installed as a **dev-only** screenshot/verification
  tool, deliberately **excluded** from `requirements.txt`.
- **D-D — `select_for_update()`** is used in the confirm/cancel exchange transactions. It is
  a no-op on SQLite (correctness rests on `atomic()` + the unique constraint + in-transaction
  re-read, as designed) but is correct on databases that support row locks.

## Open external prerequisites (not inventable)
- Company SMTP (R7) — affects M1/M10 email.
- Google OAuth credentials + approval (R8) — P9.
- Package approvals: Pillow (R14), token-encryption library (R6).
- OS cron permission (R11/R12) — timed reminders / suspension auto-expiry.
- Confirm Django 5.2 installs cleanly in the company env (R9).
