"""Root URL configuration.

Template routes + the versioned API include. Feature routes are added
per phase as their apps land.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve


def health(request):
    """Lightweight liveness check (no database access)."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("health/", health, name="health"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.skills.urls")),
    path("", include("apps.discovery.urls")),
    path("", include("apps.exchanges.urls")),
    path("", include("apps.messaging.urls")),
    path("", include("apps.scheduling.urls")),
    path("", include("apps.reviews.urls")),
    path("", include("apps.moderation.urls")),
    path("", include("apps.integrations.urls")),
    path("", include("apps.notifications.urls")),
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
]

if settings.DEBUG:
    # Serve user-uploaded media via the dev server only.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "SERVE_MEDIA", False):
    # Dev runs with DEBUG=False, where static() above is a no-op. Register the
    # media route explicitly so uploaded avatars are served (see dev.py).
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
