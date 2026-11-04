from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Registration & session
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Password reset (console email backend in dev — see R7)
    path("password-reset/", auth_views.PasswordResetView.as_view(),
         name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(),
         name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(),


         name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(),
         name="password_reset_complete"),

    # Profiles & account
    path("profile/", views.profile_detail, name="profile"),
    path("members/<int:pk>/", views.profile_detail, name="member_detail"),
    path("settings/", views.settings_edit, name="settings"),
    path("deactivate/", views.deactivate, name="deactivate"),
]
