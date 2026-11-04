from django.contrib import admin

from .models import GoogleCalendarConnection


@admin.register(GoogleCalendarConnection)
class GoogleCalendarConnectionAdmin(admin.ModelAdmin):
    list_display = ("user", "google_account_email", "connected_at", "is_revoked")
    # Tokens are never shown in the admin.
    exclude = ("access_token", "refresh_token")
    readonly_fields = ("connected_at", "token_expiry")
