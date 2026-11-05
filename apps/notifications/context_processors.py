def unread_notifications(request):
    """Expose the current user's unread notification count to all templates.

    Uses getattr so rendering never crashes when ``request.user`` is absent —
    e.g. an error page rendered before AuthenticationMiddleware has run."""
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return {
            "unread_notifications": user.notifications.filter(
                is_read=False
            ).count()
        }
    return {"unread_notifications": 0}
