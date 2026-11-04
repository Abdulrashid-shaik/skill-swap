from django.contrib import admin

from .models import ExchangeSession


@admin.register(ExchangeSession)
class ExchangeSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "exchange", "scheduled_start", "status", "google_sync_status")
    list_filter = ("status", "google_sync_status")
    search_fields = ("title",)
