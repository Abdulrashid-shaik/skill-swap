from django.urls import path

from . import views

urlpatterns = [
    path("exchanges/<int:pk>/review/", views.create_review, name="create_review"),
]
