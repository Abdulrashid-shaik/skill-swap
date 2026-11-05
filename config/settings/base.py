
"""
Base settings shared by all environments.

Environment-specific overrides live in dev.py and prod.py.
Secrets are read from the environment — never hard-code them here.
"""
import os
import sys
from pathlib import Path

# skill-swap/  (settings/ -> config/ -> project root)
BASE_DIR = Path(__file__).resolve().parents[2]

# True while running the test suite — used to keep logging quiet and avoid
# writing real log files during tests.
TESTING = "test" in sys.argv

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
    # Blocks suspended users on existing sessions (needs request.user, so it
    # runs after AuthenticationMiddleware).
    "apps.accounts.middleware.SuspensionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Rebrands bare 405 responses (Django has no 405 template hook).
    "apps.common.errors.BrandedErrorMiddleware",
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
        "OPTIONS": {
            # Begin every transaction with BEGIN IMMEDIATE so a writer takes the
            # write lock up front. Without this, SQLite's default DEFERRED mode
            # lets two transactions each read-then-try-to-write, which deadlocks
            # (SQLITE_BUSY "database is locked" that busy_timeout cannot resolve,
            # because waiting would deadlock). IMMEDIATE serializes writers: the
            # second waits for the first to commit, then sees its committed rows.
            # This is what makes the per-user exchange guard and the rate limiter
            # behave correctly under concurrency on SQLite (where
            # select_for_update is a no-op). Requires Django 5.1+.
            "transaction_mode": "IMMEDIATE",
            "timeout": 10,  # seconds to wait on a locked DB before erroring
        },
        # For SQLite, Django's test DB defaults to :memory:, whose shared-cache
        # table locks raise SQLITE_LOCKED (which busy_timeout does NOT retry),
        # so multi-connection concurrency tests cannot run representatively.
        # Use a real file so the test DB matches production: WAL + busy_timeout
        # (see apps/common/signals.py) genuinely apply and concurrent writers
        # are serialized with waits rather than erroring.
        "TEST": {"NAME": BASE_DIR / "test_db.sqlite3"},
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

# Email-login backend that also refuses suspended accounts at login time.
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.SuspensionAwareModelBackend",
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "profile"
LOGOUT_REDIRECT_URL = "home"

# RATE LIMITING ---------------------------------------------------------------
# apps/common/ratelimit uses an atomic DB counter (not Django's cache, whose
# incr() is non-atomic). Client IP for IP-based limits defaults to REMOTE_ADDR.
# Only raise this above 0 when N reverse proxies *you control* sit in front of
# the app and append to X-Forwarded-For; then the Nth-from-right XFF entry is
# trusted. Trusting a spoofable header would let attackers rotate past limits.
RATELIMIT_TRUSTED_PROXY_COUNT = int(
    os.environ.get("RATELIMIT_TRUSTED_PROXY_COUNT", "0") or "0"
)

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

# LOGGING ---------------------------------------------------------------------
# Three streams: application events ("skillswap"), security events
# ("skillswap.security": auth failures, suspension enforcement), and errors.
# Console everywhere; rotating files off-test. Level is env-tunable per
# environment (dev.py raises it to DEBUG). We deliberately log identifiers and
# paths only — NEVER passwords, tokens, session IDs, or message bodies.
LOG_DIR = BASE_DIR / "logs"
LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO").upper()

_log_handlers_app = ["console"]
_log_handlers_security = ["console"]
_log_handlers_error = ["console"]

if not TESTING:
    LOG_DIR.mkdir(exist_ok=True)
    _log_handlers_app = ["console", "app_file"]
    _log_handlers_security = ["console", "security_file"]
    _log_handlers_error = ["console", "error_file"]


def _rotating(filename, level="INFO"):
    return {
        "level": level,
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(LOG_DIR / filename),
        "maxBytes": 5 * 1024 * 1024,  # 5 MB
        "backupCount": 5,
        "formatter": "verbose",
        "delay": True,  # open the file only on first write
    }


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "level": "WARNING" if TESTING else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        **(
            {}
            if TESTING
            else {
                "app_file": _rotating("app.log"),
                "security_file": _rotating("security.log"),
                "error_file": _rotating("errors.log", level="ERROR"),
            }
        ),
    },
    "loggers": {
        # Framework: surface request errors; keep the rest at INFO.
        "django": {"handlers": _log_handlers_app, "level": "INFO", "propagate": False},
        "django.request": {
            "handlers": _log_handlers_error,
            "level": "ERROR",
            "propagate": False,
        },
        # Application events (exchange transitions, etc.).
        "skillswap": {
            "handlers": _log_handlers_app,
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # Security events: auth failures, suspension enforcement. Separate file.
        "skillswap.security": {
            "handlers": _log_handlers_security,
            "level": "INFO",
            "propagate": False,
        },
    },
}

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
    # Translate service-layer BusinessRuleError into clean 400 responses.
    "EXCEPTION_HANDLER": "apps.common.drf.exception_handler",
}



# URL prefix handling (see ForwardedPrefixMiddleware), in priority order:
#   1. APP_URL_PREFIX (above) — explicit, for strip-and-no-header proxies.
#   2. X-Forwarded-Prefix header — reverse proxies that strip + announce it.
#   3. /absproxy/<port>/ embedded in the path — code-server forwards it whole.
# All three are opt-in per request/environment, so direct access is unaffected.
# We deliberately avoid Django's FORCE_SCRIPT_NAME: it prepends the prefix to
# generated URLs but never strips it from the inbound path, so /absproxy/ routes
# would 404. The middleware does both.