from django.urls import path

from . import views

urlpatterns = [
    path("exchanges/<int:pk>/chat/", views.chat, name="exchange_chat"),
    path("exchanges/<int:pk>/messages/", views.messages_poll, name="messages_poll"),
    path("exchanges/<int:pk>/messages/send/", views.messages_send, name="messages_send"),
]
