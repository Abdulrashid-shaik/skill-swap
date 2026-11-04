from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.common.models import TimeStampedModel


class RequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class ExchangeStatus(models.TextChoices):
    ONGOING = "ongoing", "Ongoing"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class ExchangeRequest(TimeStampedModel):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requests_sent")
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requests_received")
    # What the sender will teach, and what the sender wants to learn.
    offered_skill = models.ForeignKey(
        "skills.Skill", on_delete=models.PROTECT, related_name="+")
    requested_skill = models.ForeignKey(
        "skills.Skill", on_delete=models.PROTECT, related_name="+")
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # At most one PENDING request per (sender, receiver).
            models.UniqueConstraint(
                fields=["sender", "receiver"],
                condition=Q(status="pending"),
                name="uniq_pending_request_per_pair",
            ),
            models.CheckConstraint(
                condition=~Q(sender=F("receiver")), name="request_not_self"),
        ]
        indexes = [
            models.Index(fields=["receiver", "status"]),
            models.Index(fields=["sender", "status"]),
        ]

    def __str__(self):
        return f"{self.sender} -> {self.receiver} ({self.status})"


class Exchange(TimeStampedModel):
    request = models.OneToOneField(
        ExchangeRequest, on_delete=models.PROTECT, related_name="exchange")
    participant_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="exchanges_as_a")
    participant_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="exchanges_as_b")
    skill_a_teaches = models.ForeignKey(
        "skills.Skill", on_delete=models.PROTECT, related_name="+")
    skill_b_teaches = models.ForeignKey(
        "skills.Skill", on_delete=models.PROTECT, related_name="+")
    status = models.CharField(
        max_length=10, choices=ExchangeStatus.choices, default=ExchangeStatus.ONGOING)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+")
    progress_note = models.TextField(blank=True)

    @property
    def participants(self):
        return [self.participant_a, self.participant_b]

    def includes(self, user):
        return user.pk in (self.participant_a_id, self.participant_b_id)

    def other_participant(self, user):
        return self.participant_b if user.pk == self.participant_a_id else self.participant_a

    def has_confirmed(self, user):
        return self.confirmations.filter(user=user).exists()

    def __str__(self):
        return f"Exchange<{self.participant_a} / {self.participant_b}> ({self.status})"


class ExchangeConfirmation(TimeStampedModel):
    """One row per participant who has confirmed completion. The exchange only
    completes when BOTH participants have a row (see services.confirm_exchange).
    The frontend never decides completion."""

    exchange = models.ForeignKey(
        Exchange, on_delete=models.CASCADE, related_name="confirmations")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    confirmed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["exchange", "user"], name="uniq_exchange_confirmation"),
        ]

    def __str__(self):
        return f"{self.user} confirmed {self.exchange_id}"
