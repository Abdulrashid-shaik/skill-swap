from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from .validators import validate_avatar_size


class UserManager(BaseUserManager):
    """Email-based manager (no username required). See docs/DECISIONS.md R2."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user: email is the login identifier; username is an optional
    display handle (not unique). Deactivation and suspension are moderation
    states distinct from Django's is_active."""

    # Email is the unique login identifier.
    email = models.EmailField("email address", unique=True)

    # Optional, non-unique display handle (overrides AbstractUser.username).
    username = models.CharField(max_length=150, blank=True, null=True)

    # Self-service deactivation (M1).
    is_deactivated = models.BooleanField(default=False)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    # Moderation suspension (M12 / R12). suspended_until optional auto-expiry.
    is_suspended = models.BooleanField(default=False)
    suspended_until = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # createsuperuser prompts email + password only

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def is_currently_suspended(self) -> bool:
        """True iff the account is under an *active* suspension. A suspension
        with a ``suspended_until`` in the past has expired and no longer counts
        (R12 auto-expiry). ``suspended_until=None`` means an indefinite
        suspension. Deactivation is a separate state (enforced via is_active)."""
        if not self.is_suspended:
            return False
        if self.suspended_until is not None and self.suspended_until <= timezone.now():
            return False
        return True

    def lift_suspension_if_expired(self) -> bool:
        """Persist auto-expiry: clear a suspension whose ``suspended_until`` has
        passed, so the member regains access without admin action (R12). Called
        lazily at authentication and request time. Returns True if it cleared."""
        if (
            self.is_suspended
            and self.suspended_until is not None
            and self.suspended_until <= timezone.now()
        ):
            self.is_suspended = False
            self.suspended_until = None
            self.save(update_fields=["is_suspended", "suspended_until"])
            return True
        return False


class ExperienceLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"
    EXPERT = "expert", "Expert"


class UserProfile(TimeStampedModel):
    """Presentation fields for a member (M2)."""

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="profile"
    )
    full_name = models.CharField(max_length=150, blank=True)
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_avatar_size,
        ],
    )
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    experience_level = models.CharField(
        max_length=20, choices=ExperienceLevel.choices, blank=True
    )

    # Denormalized caches, maintained by reviews/exchanges in later phases.
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)
    completed_exchanges = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Profile<{self.user.email}>"
