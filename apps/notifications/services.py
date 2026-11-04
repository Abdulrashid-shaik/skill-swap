from .models import Notification


def notify(recipient, type, title, *, target_url="", body=""):
    """Create an in-app notification. Safe to call from within request/exchange
    transactions — a single INSERT."""
    return Notification.objects.create(
        recipient=recipient, type=type, title=title,
        target_url=target_url, body=body,
    )
