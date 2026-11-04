# Architecture

A modular Django monolith: one project, one configuration package, 11 focused apps. Each app owns its models, serializers, views, templates, and tests. Pages are server-rendered Django templates; DRF provides JSON endpoints that vanilla JS calls with `fetch` for dynamic interactions. No SPA, no build step.

## Project layout

```
skill-swap/
├── manage.py
├── requirements.txt            # pinned; additions require approval
├── .env                        # real secrets (gitignored, if env permits)
├── .env.example                # placeholders only (committed)
├── .gitignore
├── config/                     # central configuration package
│   ├── settings/
│   │   ├── base.py             # shared settings, INSTALLED_APPS, DRF, USE_TZ=True
│   │   ├── dev.py              # DEBUG, SQLite+WAL, console email backend
│   │   └── prod.py             # secure cookies, HSTS, ALLOWED_HOSTS, HTTPS
│   ├── urls.py                 # root URLconf: template routes + /api/v1 router
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── common/                 # TimeStampedModel, mixins, base permissions, pagination, error handler
│   ├── accounts/               # custom User, UserProfile, auth, deactivation, suspension
│   ├── skills/                 # SkillCategory, Skill (approval workflow), UserSkill
│   ├── discovery/              # mutual-matching service + views (model-light)
│   ├── exchanges/              # ExchangeRequest, Exchange, ExchangeConfirmation
│   ├── messaging/              # Message
│   ├── scheduling/             # ExchangeSession (timezone-aware)
│   ├── integrations/           # GoogleCalendarConnection + Google service layer (P9, feature-flagged)
│   ├── notifications/          # Notification
│   ├── reviews/                # Review
│   └── moderation/             # UserBlock, UserReport, admin moderation
├── templates/                  # base.html + per-app templates + partials
├── static/
│   ├── css/                    # design-system tokens + component styles
│   ├── js/                     # api.js (fetch+CSRF) + per-feature modules
│   └── images/
├── media/                      # user uploads, e.g. avatars (gitignored)
└── docs/                       # this documentation set
```

## App responsibilities

| App | Owns | Notes |
|---|---|---|
| `common` | base model, shared mixins, base permission classes, pagination, consistent error envelope, context processors | no business models |
| `accounts` | `User`, `UserProfile` | custom User from P2 (email login, optional username); deactivation + suspension flags |
| `skills` | `SkillCategory`, `Skill`, `UserSkill` | canonical catalogue; suggest→approve; OFFER/WANT via `kind` enum |
| `discovery` | matching service + discovery/search views | **logic-heavy, model-light**; on-demand ORM queries |
| `exchanges` | `ExchangeRequest`, `Exchange`, `ExchangeConfirmation` | request lifecycle + dual confirmation |
| `messaging` | `Message` | exchange-scoped; participant-only; JS polling |
| `scheduling` | `ExchangeSession` | tz-aware; reschedule chain; Google fields (nullable) |
| `integrations` | `GoogleCalendarConnection`, Google service layer | isolated + feature-flagged; app runs without it |
| `notifications` | `Notification` | DB-backed; `type` + `target_url` |
| `reviews` | `Review` | post-completion; updates profile aggregate |
| `moderation` | `UserBlock`, `UserReport`, admin views | block/report/suspend/approve-skill |

## Key structural decisions (see DECISIONS.md)

- **Custom `accounts.User` from P2** — changing `AUTH_USER_MODEL` later forces a painful migration.
- **`discovery` is model-light** — matching is a query, not stored state; no Redis/queue means on-demand computation.
- **`integrations` is isolated and feature-flagged** — P1–P8 ship with zero Google dependency; Google is the only externally-blocked phase.
- **Template-first + DRF JSON** — progressive enhancement; core flows work without JS, `fetch` upgrades interactivity.

## Request flow

1. Browser requests a page → Django view renders a template (`base.html` → app template → partials).
2. Interactive actions (send request, confirm completion, poll chat, load matches) → vanilla JS `fetch` → `/api/v1/...` DRF endpoint.
3. DRF enforces session auth + CSRF + object-level permissions, runs serializer validation and business rules, returns JSON.
4. JS updates the DOM in place.

Render order for caching and clarity: settings → URLconf (templates + `/api/v1` router) → app views.

## Settings profiles

- `base.py`: `INSTALLED_APPS`, DRF config (session auth, pagination, throttles), `USE_TZ=True`, password validators, media/static.
- `dev.py`: `DEBUG=True`, SQLite with WAL pragma, console email backend.
- `prod.py`: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_*`, `ALLOWED_HOSTS`, secrets from env.

See [DATABASE_ERD.md](DATABASE_ERD.md) for entities, [API_DESIGN.md](API_DESIGN.md) for endpoints, [BUSINESS_RULES.md](BUSINESS_RULES.md) for state machines.
