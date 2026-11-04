from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.utils import unique_slugify


class SkillCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "skill categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SkillStatus(models.TextChoices):
    PENDING = "pending", "Pending approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Skill(TimeStampedModel):
    """Canonical catalogue entry. User suggestions start PENDING and only
    become discoverable once an administrator approves them (R13)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    category = models.ForeignKey(
        SkillCategory, on_delete=models.PROTECT, related_name="skills"
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=SkillStatus.choices, default=SkillStatus.PENDING
    )
    suggested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggested_skills",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "category"], name="uniq_skill_name_per_category"
            )
        ]
        indexes = [models.Index(fields=["status", "is_active"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)

    @property
    def is_available(self):
        return self.status == SkillStatus.APPROVED and self.is_active

    def __str__(self):
        return self.name


class SkillKind(models.TextChoices):
    OFFER = "offer", "Can teach"
    WANT = "want", "Wants to learn"


class Proficiency(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"
    EXPERT = "expert", "Expert"


class UserSkill(TimeStampedModel):
    """A skill a user can teach (OFFER) or wants to learn (WANT). One row per
    (user, skill, kind). Proficiency is meaningful for OFFER."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_skills"
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.PROTECT, related_name="user_skills"
    )
    kind = models.CharField(max_length=5, choices=SkillKind.choices)
    proficiency = models.CharField(
        max_length=20, choices=Proficiency.choices, blank=True
    )
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "skill", "kind"], name="uniq_user_skill_kind"
            )
        ]
        indexes = [models.Index(fields=["skill", "kind", "is_active"])]

    def __str__(self):
        return f"{self.user} {self.kind} {self.skill}"
