from django.urls import path

from . import views

urlpatterns = [
    path("members/<int:pk>/request/", views.send_request, name="send_request"),
    path("requests/sent/", views.requests_sent, name="requests_sent"),
    path("requests/received/", views.requests_received, name="requests_received"),
    path("requests/<int:pk>/accept/", views.accept_request, name="accept_request"),
    path("requests/<int:pk>/reject/", views.reject_request, name="reject_request"),
    path("requests/<int:pk>/cancel/", views.cancel_request, name="cancel_request"),
    path("exchanges/", views.exchange_list, name="exchange_list"),
    path("exchanges/<int:pk>/", views.exchange_detail, name="exchange_detail"),
    path("exchanges/<int:pk>/confirm/", views.confirm_exchange, name="confirm_exchange"),
    path("exchanges/<int:pk>/cancel/", views.cancel_exchange, name="cancel_exchange"),
]
