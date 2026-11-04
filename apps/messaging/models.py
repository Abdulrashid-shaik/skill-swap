from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Message(TimeStampedModel):
    exchange = models.ForeignKey(
        "exchanges.Exchange", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["exchange", "created_at"]),
            models.Index(fields=["exchange", "is_read"]),
        ]

    def __str__(self):
        return f"msg<{self.exchange_id}> from {self.sender_id}"
