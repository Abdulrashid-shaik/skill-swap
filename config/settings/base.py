
"""
Base settings shared by all environments.

Environment-specific overrides live in dev.py and prod.py.
Secrets are read from the environment — never hard-code them here.
"""
import os
from pathlib import Path

# skill-swap/  (settings/ -> config/ -> project root)
BASE_DIR = Path(__file__).resolve().parents[2]

# SECURITY --------------------------------------------------------------------
# Dev-only insecure fallback; prod.py requires a real key from the environment.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me"
)
DEBUG = False
ALLOWED_HOSTS: list[str] = []

# APPLICATIONS ----------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.skills",
    "apps.moderation",
    "apps.discovery",
    "apps.notifications",
    "apps.exchanges",
    "apps.messaging",
    "apps.scheduling",
    "apps.reviews",
    "apps.integrations",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "apps.common.middleware.ForwardedPrefixMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.notifications.context_processors.unread_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# DATABASE --------------------------------------------------------------------
# SQLite only. WAL mode + pragmas are applied per-connection in
# apps/common/signals.py (connection_created signal).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# PASSWORD VALIDATION ---------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# AUTHENTICATION --------------------------------------------------------------
# Custom user model from the start (email login). Changing AUTH_USER_MODEL
# after the first migration is extremely painful — see docs/DECISIONS.md ADR-1.
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "profile"
LOGOUT_REDIRECT_URL = "home"

# INTERNATIONALIZATION / TIME -------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True  # timezone-aware datetimes (required for scheduling, M8)

# URL PREFIX (path-prefix proxies) --------------------------------------------
# Some environments mount the app under a sub-path. Two proxy styles exist:
#
#   * code-server ``/absproxy/<port>/`` forwards the FULL path through, so
#     ForwardedPrefixMiddleware auto-detects the prefix from the path — nothing
#     to configure here.
#   * code-server ``/proxy/<port>/`` (and similar) STRIP the sub-path before
#     forwarding and send no ``X-Forwarded-Prefix`` header, so the app has no
#     way to discover it. For those, set ``APP_URL_PREFIX`` so every generated
#     link, redirect and asset URL is prefixed, e.g.::
#
#         APP_URL_PREFIX=/proxy/8899
#
# Empty (the default) = direct access / auto-detected proxy — unaffected.
APP_URL_PREFIX = os.environ.get("APP_URL_PREFIX", "").strip()
if APP_URL_PREFIX:
    APP_URL_PREFIX = "/" + APP_URL_PREFIX.strip("/")

# STATIC & MEDIA --------------------------------------------------------------
# Root-absolute URLs (leading "/") so assets resolve from the mount root rather
# than relative to the current page. STATIC_URL carries the configured prefix
# directly; MEDIA_URL stays prefix-less and ProxyAwareMediaStorage prepends the
# *live* script prefix per request (covers both auto-detected and configured
# proxies) — see apps/common/storage.py.
STATIC_URL = f"{APP_URL_PREFIX}/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Uploaded media is served through a storage that prefixes its URLs with the
# active script prefix, so avatars load when the app is reached under a
# path-prefix proxy (see apps/common/storage.py + ForwardedPrefixMiddleware).
STORAGES = {
    "default": {
        "BACKEND": "apps.common.storage.ProxyAwareMediaStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# GOOGLE CALENDAR / MEET (P9) -------------------------------------------------
# Off until OAuth credentials AND the Google client libraries are provided
# (external prerequisites — see docs/DECISIONS.md R6/R8). The rest of the app
# runs fully without it; all integration code is isolated in apps/integrations.
GOOGLE_INTEGRATION_ENABLED = (
    os.environ.get("GOOGLE_INTEGRATION_ENABLED", "false").lower() == "true"
)
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")

# DJANGO REST FRAMEWORK -------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/min",
        "user": "120/min",
    },

}



# URL prefix handling (see ForwardedPrefixMiddleware), in priority order:
#   1. APP_URL_PREFIX (above) — explicit, for strip-and-no-header proxies.
#   2. X-Forwarded-Prefix header — reverse proxies that strip + announce it.
#   3. /absproxy/<port>/ embedded in the path — code-server forwards it whole.
# All three are opt-in per request/environment, so direct access is unaffected.
# We deliberately avoid Django's FORCE_SCRIPT_NAME: it prepends the prefix to
# generated URLs but never strips it from the inbound path, so /absproxy/ routes
# would 404. The middleware does both.