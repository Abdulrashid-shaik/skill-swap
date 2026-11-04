from django.contrib import admin

from .models import Exchange, ExchangeConfirmation, ExchangeRequest


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("sender__email", "receiver__email")


class ConfirmationInline(admin.TabularInline):
    model = ExchangeConfirmation
    extra = 0


@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ("id", "participant_a", "participant_b", "status", "started_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("participant_a__email", "participant_b__email")
    inlines = [ConfirmationInline]
