"""Account-related signal receivers: profile creation and security logging."""
import logging

from django.contrib.auth.signals import user_login_failed, user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, UserProfile

security_logger = logging.getLogger("skillswap.security")


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(user_login_failed)
def log_login_failed(sender, credentials=None, request=None, **kwargs):
    """Record failed authentication attempts for monitoring/brute-force review.
    Django censors the password in ``credentials`` before this fires, so only
    the attempted identifier is logged — never the secret."""
    identifier = ""
    if credentials:
        identifier = credentials.get("username") or credentials.get("email") or ""
    security_logger.warning("Failed login attempt for identifier=%r", identifier)


@receiver(user_logged_in)
def log_login_success(sender, user, request=None, **kwargs):
    security_logger.info("Login succeeded for account id=%s", user.pk)
