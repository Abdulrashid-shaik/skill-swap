from django.urls import path

from . import views

urlpatterns = [
    path("skills/", views.catalogue, name="skill_catalogue"),
    path("skills/suggest/", views.suggest_skill, name="suggest_skill"),
    path("my-skills/", views.my_skills, name="my_skills"),
    path("my-skills/<int:pk>/remove/", views.remove_user_skill, name="remove_user_skill"),
]
