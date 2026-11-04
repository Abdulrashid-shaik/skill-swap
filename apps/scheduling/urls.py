from django.urls import path

from . import views

urlpatterns = [
    path("exchanges/<int:pk>/sessions/", views.session_list, name="session_list"),
    path("sessions/<int:pk>/reschedule/", views.reschedule_session, name="reschedule_session"),
    path("sessions/<int:pk>/cancel/", views.cancel_session, name="cancel_session"),
    path("sessions/<int:pk>/complete/", views.complete_session, name="complete_session"),
]
