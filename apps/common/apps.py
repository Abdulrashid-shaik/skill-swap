from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"

    def ready(self):
        # Register the SQLite PRAGMA signal handler (WAL, foreign keys, etc.).
        from . import signals  # noqa: F401
