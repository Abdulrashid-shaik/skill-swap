from django.contrib import admin
from django.utils import timezone

from .models import UserBlock, UserReport


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ("blocker", "blocked", "created_at")
    search_fields = ("blocker__email", "blocked__email")


@admin.action(description="Mark selected reports resolved")
def mark_resolved(modeladmin, request, queryset):
    queryset.update(status="resolved", handled_by=request.user, handled_at=timezone.now())


@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ("reporter", "reported", "reason", "status", "created_at", "handled_by")
    list_filter = ("status", "reason")
    search_fields = ("reporter__email", "reported__email")
    actions = (mark_resolved,)
