# SkillSwap

**A non-monetary, peer-to-peer skill exchange platform.** Members trade skills
with each other — never money. You offer what you can teach, find someone who
wants it and teaches something you want, and the two of you run an exchange:
request → accept → shared workspace → chat → scheduled sessions →
**dual-confirmed completion** → mutual review.

> No payments, credits, or points. No public feed. No AI features. Just people
> swapping skills.

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.12+ |
| Framework | Django 5.2 LTS |
| API | Django REST Framework |
| Database | SQLite |
| Frontend | Django Templates + vanilla JS (CSS/JS inlined — proxy-safe) |
| Auth | Session auth + CSRF, custom email-login `User` model |

Dependencies are pinned in [`requirements.txt`](requirements.txt):
`Django`, `djangorestframework`, `Pillow`.

---

## Quick start

Requires **Python 3.12+**. From the project root (`skill-swap/`):

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations (creates db.sqlite3)
python manage.py migrate

# 4. (Optional) create an admin account for the Django admin / moderation
python manage.py createsuperuser

# 5. Run the development server
python manage.py runserver
```

Then open **http://127.0.0.1:8000/**.

`manage.py` loads `config.settings.dev` by default, so no environment variables
are needed for local development.

### Running on a specific host/port

```bash
python manage.py runserver 0.0.0.0:8011   # bind all interfaces, port 8011
```

---

## Running behind a path-prefix proxy (code-server / VS Code / reverse proxy)

The app works unchanged on a direct URL **and** when served under a path prefix,
so you can open it through a browser IDE's port forwarder or a reverse proxy
without editing any settings.

- **code-server / VS Code** — start the server (e.g. `python manage.py runserver
  127.0.0.1:8011`) and open it through the **`/absproxy/<port>/`** path, matching
  the port you ran on:

  ```
  https://<your-host>:<code-server-port>/absproxy/8011/
  ```

  Use `/absproxy/` (not `/proxy/`): it passes the full path through so the app
  can generate correctly-prefixed links. `ForwardedPrefixMiddleware`
  (`apps/common/middleware.py`) detects the prefix automatically — nothing to
  configure.

- **nginx / Caddy / ingress** — strip the prefix before forwarding and set the
  `X-Forwarded-Prefix` header; the same middleware honors it.

If the proxy terminates TLS (browser uses `https://`) and the host/port differs
from the default, add the public origin so POST forms pass CSRF:

```bash
export CSRF_TRUSTED_ORIGINS="https://your-host:port"
python manage.py runserver 127.0.0.1:8011
```

---

## Running the tests

```bash
python manage.py test
```

The suite covers models, business rules (including dual confirmation), views,
and the proxy/path-prefix middleware.

---

## Project layout

```
skill-swap/
├── config/            # settings (base/dev/prod), root URLs, WSGI/ASGI
├── apps/
│   ├── common/        # shared middleware, storage, template tags, utils
│   ├── accounts/      # custom User, profiles, auth
│   ├── skills/        # skill catalogue, user skills, approval
│   ├── discovery/     # mutual-match discovery
│   ├── exchanges/     # requests + exchange workspace, dual confirmation
│   ├── messaging/     # per-exchange chat
│   ├── scheduling/    # exchange sessions
│   ├── reviews/       # post-exchange mutual reviews
│   ├── moderation/    # blocking, reporting, admin moderation
│   ├── notifications/ # in-app notifications
│   └── integrations/  # Google Calendar/Meet (feature-flagged off by default)
├── templates/         # Django templates (Sky-Blue design system)
├── docs/              # source-of-truth design docs (see below)
├── manage.py
└── requirements.txt
```

---

## Documentation

The [`docs/`](docs/) directory is the source of truth for design and scope:

- [`PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md) — vision, rules, locked stack
- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) — apps, config, request flow
- [`DATABASE_ERD.md`](docs/DATABASE_ERD.md) — entities and constraints
- [`BUSINESS_RULES.md`](docs/BUSINESS_RULES.md) — matching, state machines, dual confirmation
- [`API_DESIGN.md`](docs/API_DESIGN.md) — `/api/v1/` conventions
- [`UI_DESIGN_SYSTEM.md`](docs/UI_DESIGN_SYSTEM.md) — design system, pages, voice
- [`DEVELOPMENT_ROADMAP.md`](docs/DEVELOPMENT_ROADMAP.md) — phases + acceptance criteria
- [`DEPLOYMENT.md`](docs/DEPLOYMENT.md) — production configuration
- [`DECISIONS.md`](docs/DECISIONS.md) — architecture decisions and the decision log

---

## Configuration notes

- **Settings modules** live in `config/settings/`: `dev.py` (default) and
  `prod.py`. Production reads `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS`
  from the environment — see [`.env.example`](.env.example) and
  [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
- **Email** prints to the console in development (no SMTP required).
- **Google Calendar/Meet** integration is feature-flagged **off**; the whole app
  runs without it.
- `db.sqlite3` and uploaded `media/` are git-ignored — a fresh clone starts with
  an empty database after `migrate`.
