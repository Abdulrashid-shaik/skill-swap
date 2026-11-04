from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class NotificationType(models.TextChoices):
    REQUEST_RECEIVED = "request_received", "New exchange request"
    REQUEST_ACCEPTED = "request_accepted", "Request accepted"
    REQUEST_REJECTED = "request_rejected", "Request rejected"
    REQUEST_CANCELLED = "request_cancelled", "Request cancelled"
    MESSAGE_RECEIVED = "message_received", "New message"
    SESSION_SCHEDULED = "session_scheduled", "Session scheduled"
    SESSION_RESCHEDULED = "session_rescheduled", "Session rescheduled"
    SESSION_CANCELLED = "session_cancelled", "Session cancelled"
    CONFIRMATION_RECORDED = "confirmation_recorded", "Completion confirmed by partner"
    EXCHANGE_COMPLETED = "exchange_completed", "Exchange completed"
    EXCHANGE_CANCELLED = "exchange_cancelled", "Exchange cancelled"
    REVIEW_RECEIVED = "review_received", "New review"


class Notification(TimeStampedModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=32, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    target_url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "created_at"])]

    def __str__(self):
        return f"{self.get_type_display()} -> {self.recipient}"
