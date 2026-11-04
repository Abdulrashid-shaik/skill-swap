from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", views.mark_read, name="notification_read"),
    path("notifications/read-all/", views.mark_all_read, name="notification_read_all"),
]
