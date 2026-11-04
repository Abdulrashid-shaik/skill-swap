from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class SessionStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    RESCHEDULED = "rescheduled", "Rescheduled"


class GoogleSyncStatus(models.TextChoices):
    NONE = "none", "Not synced"
    PENDING = "pending", "Pending"
    SYNCED = "synced", "Synced"
    FAILED = "failed", "Failed"


class ExchangeSession(TimeStampedModel):
    exchange = models.ForeignKey(
        "exchanges.Exchange", on_delete=models.CASCADE, related_name="sessions")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    scheduled_start = models.DateTimeField()  # tz-aware (USE_TZ=True)
    scheduled_end = models.DateTimeField()
    status = models.CharField(
        max_length=12, choices=SessionStatus.choices, default=SessionStatus.SCHEDULED)
    previous_session = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    # Google Calendar / Meet (populated in P9; app works without them).
    google_event_id = models.CharField(max_length=200, blank=True)
    google_meet_link = models.URLField(blank=True)
    google_sync_status = models.CharField(
        max_length=10, choices=GoogleSyncStatus.choices, default=GoogleSyncStatus.NONE)

    class Meta:
        ordering = ["scheduled_start"]
        indexes = [models.Index(fields=["exchange", "scheduled_start"])]

    def __str__(self):
        return f"{self.title} ({self.status})"
