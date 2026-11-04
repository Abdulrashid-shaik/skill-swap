# Deployment & Operations

## Requirements
- Python 3.12+, the packages in `requirements.txt` (`Django`, `djangorestframework`, `Pillow`).
- SQLite (bundled with Python). WAL mode is enabled automatically (`apps/common/signals.py`).

## Local development
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser        # email + password
python manage.py runserver              # http://127.0.0.1:8000/
```
Default settings module is `config.settings.dev` (DEBUG on, console email backend,
permissive `ALLOWED_HOSTS` for dev proxies).

## Production
Use `config.settings.prod` and provide secrets via environment (never commit them):

| Env var | Purpose |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `DJANGO_SECRET_KEY` | **required** — long random string |
| `DJANGO_ALLOWED_HOSTS` | comma-separated hostnames |

`prod.py` enables `SECURE_SSL_REDIRECT`, secure + HSTS cookies, and `SECURE_PROXY_SSL_HEADER`.

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
export DJANGO_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(64))')"
export DJANGO_ALLOWED_HOSTS="skillswap.example.com"
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy          # should report no issues
# Serve via gunicorn/uwsgi behind nginx; serve STATIC_ROOT and MEDIA_ROOT.
gunicorn config.wsgi:application
```

> **Static/media:** in production, serve `STATIC_ROOT` (`collectstatic`) and `MEDIA_ROOT`
> via the web server. In this environment the design-system CSS is also inlined into the
> page (`apps/common/templatetags/assets.py`) so styling survives path-rewriting proxies —
> see docs/DECISIONS.md.

## SQLite notes
- One writer at a time. Keep write transactions short (they are — see
  `BUSINESS_RULES.md`). WAL improves read/write concurrency. Fine for the expected
  scale; revisit only if write contention appears.
- Back up `db.sqlite3` (and `-wal`/`-shm`) with the app stopped, or use `.backup`.

## Optional integrations (external prerequisites)
- **Email (verification + notifications):** set `EMAIL_*` env vars and swap the email
  backend when company SMTP is available (R7). Password reset already works via the
  console backend in dev.
- **Google Calendar / Meet (P9):** set `GOOGLE_INTEGRATION_ENABLED=true` plus
  `GOOGLE_OAUTH_CLIENT_ID/SECRET/REDIRECT_URI`, and install the Google client libraries
  (`google-auth google-auth-oauthlib google-api-python-client`) — an approval-gated
  install. Until then the app runs fully with the integration off. See
  `apps/integrations/` and DECISIONS.md R6/R8.

## Seeding a catalogue
Categories/skills are admin-managed. Create them in `/admin/` or via a data script.
The app ships no fabricated users, activity, or reviews.
