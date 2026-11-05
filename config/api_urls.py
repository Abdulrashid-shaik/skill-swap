"""Versioned API URLconf (/api/v1/).

A focused REST surface over the existing service layer (session auth + CSRF,
IsAuthenticated by default). Business rules live in the services these views
call — not here. Administrative/moderation *handling* is intentionally NOT
exposed; ordinary users can only file reports.
"""
from django.urls import path

from apps.accounts.api import MeView, MemberProfileView
from apps.discovery.api import DiscoverView
from apps.exchanges.api import (ExchangeCancelView, ExchangeConfirmView,
                                ExchangeDetailView, ExchangeListView,
                                RequestActionView, RequestCreateView,
                                RequestListView)
from apps.messaging.api import MessageListView, MessageSendView
from apps.moderation.api import ReportCreateView
from apps.notifications.api import (NotificationListView,
                                    NotificationMarkAllReadView,
                                    NotificationMarkReadView)
from apps.skills.api import (MySkillDeleteView, MySkillsView,
                             SkillCatalogueView)

app_name = "api"

urlpatterns = [
    # Profiles
    path("me/", MeView.as_view(), name="me"),
    path("members/<int:pk>/", MemberProfileView.as_view(), name="member"),
    path("members/<int:pk>/report/", ReportCreateView.as_view(), name="member_report"),

    # Skills & discovery
    path("skills/", SkillCatalogueView.as_view(), name="skills"),
    path("my-skills/", MySkillsView.as_view(), name="my_skills"),
    path("my-skills/<int:pk>/", MySkillDeleteView.as_view(), name="my_skill_delete"),
    path("discover/", DiscoverView.as_view(), name="discover"),

    # Exchange requests
    path("requests/", RequestListView.as_view(), name="requests"),
    path("requests/create/", RequestCreateView.as_view(), name="request_create"),
    path("requests/<int:pk>/<str:action>/", RequestActionView.as_view(),
         name="request_action"),

    # Exchanges
    path("exchanges/", ExchangeListView.as_view(), name="exchanges"),
    path("exchanges/<int:pk>/", ExchangeDetailView.as_view(), name="exchange_detail"),
    path("exchanges/<int:pk>/confirm/", ExchangeConfirmView.as_view(),
         name="exchange_confirm"),
    path("exchanges/<int:pk>/cancel/", ExchangeCancelView.as_view(),
         name="exchange_cancel"),

    # Messaging
    path("exchanges/<int:pk>/messages/", MessageListView.as_view(),
         name="messages"),
    path("exchanges/<int:pk>/messages/send/", MessageSendView.as_view(),
         name="message_send"),

    # Notifications
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/<int:pk>/read/", NotificationMarkReadView.as_view(),
         name="notification_read"),
    path("notifications/read-all/", NotificationMarkAllReadView.as_view(),
         name="notification_read_all"),
]
