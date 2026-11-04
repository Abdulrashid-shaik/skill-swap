"""Development settings. Loaded by default via manage.py."""
import os

from .base import *  # noqa: F401,F403

DEBUG = False
# Dev only: accept any Host header so the app works behind the environment's
# port-forwarding (e.g. 10.10.0.36:<port>). Production uses a strict,
# env-driven ALLOWED_HOSTS (see prod.py) — never ship "*".
ALLOWED_HOSTS = ["*"]

# If a reverse proxy announces the real scheme, honor it (harmless when absent).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# The browser talks HTTPS to code-server, but code-server forwards to this dev
# server over plain HTTP *without* X-Forwarded-Proto. Django therefore thinks
# the request is HTTP and, on every POST, rejects the browser's
# ``Origin: https://<host>:<port>`` as a scheme mismatch (CSRF 403 — the logout
# "error" you saw). Trusting the exact proxy origin(s) makes those POSTs pass.
# Override with a comma-separated env var when the host/port differs.
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CSRF_TRUSTED_ORIGINS", "https://10.10.0.36:8159"
    ).split(",")
    if o.strip()
]


# Dev runs with DEBUG=False, which disables Django's static() media helper.
# Serve uploaded media (avatars) explicitly so they load in development.
# In production a real web server serves /media/, so this stays off there.
SERVE_MEDIA = True

# Email prints to the console in development (no SMTP required).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Reaching this dev server through code-server's path-prefix proxy?
#   * /absproxy/<port>/ forwards the whole path → auto-detected, nothing to do.
#   * /proxy/<port>/ strips the path and sends no header → export APP_URL_PREFIX
#     so links stay inside the mount, e.g.:
#         APP_URL_PREFIX=/proxy/8899 python manage.py runserver 0.0.0.0:8899
# See config/settings/base.py (APP_URL_PREFIX) for details.
