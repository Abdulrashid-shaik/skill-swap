from django.urls import path

from . import views

urlpatterns = [
    path("members/<int:pk>/block/", views.block, name="block_user"),
    path("members/<int:pk>/unblock/", views.unblock, name="unblock_user"),
    path("members/<int:pk>/report/", views.report, name="report_user"),
]
