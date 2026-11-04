from django.urls import path

from . import views

urlpatterns = [
    path("integrations/google/connect/", views.connect, name="google_connect"),
    path("integrations/google/callback/", views.callback, name="google_callback"),
    path("integrations/google/disconnect/", views.disconnect, name="google_disconnect"),
]
