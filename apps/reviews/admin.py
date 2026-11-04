from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("reviewer", "reviewee", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("reviewer__email", "reviewee__email")
