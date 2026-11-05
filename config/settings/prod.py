"""Production settings. Requires secrets from the environment."""
import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

# Required in production — fail loudly if missing.
try:
    SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
except KeyError as exc:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set in production."
    ) from exc

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if h.strip()
]
# An empty ALLOWED_HOSTS with DEBUG=False rejects every request; refuse to boot
# with a clear error instead of a confusing 400 on the first request. Never
# allow "*" here (it disables Host-header validation).
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be set (comma-separated hostnames) in "
        "production; '*' is not permitted."
    )
if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must not contain '*' in production."
    )

# Secure cookies & transport.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
