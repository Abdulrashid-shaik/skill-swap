from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("exchange", "sender", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("sender__email", "body")
