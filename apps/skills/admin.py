from django.contrib import admin

from .models import Skill, SkillCategory, SkillStatus, UserSkill


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.action(description="Approve selected skills")
def approve_skills(modeladmin, request, queryset):
    queryset.update(status=SkillStatus.APPROVED)


@admin.action(description="Reject selected skills")
def reject_skills(modeladmin, request, queryset):
    queryset.update(status=SkillStatus.REJECTED)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "status", "is_active", "suggested_by")
    list_filter = ("status", "is_active", "category")
    search_fields = ("name",)
    autocomplete_fields = ("category",)
    actions = (approve_skills, reject_skills)


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "kind", "proficiency", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("user__email", "skill__name")
