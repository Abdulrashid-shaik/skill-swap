import re

from django.urls import set_script_prefix

# code-server (and VS Code) expose a local port at ``/absproxy/<port>/`` and
# forward the FULL path through (unlike ``/proxy/<port>/``, which strips it but
# tells the backend nothing). We detect that prefix from the path itself.
_ABSPROXY_PREFIX = re.compile(r"^/(?:abs)?proxy/\d+")


class ForwardedPrefixMiddleware:
    """Make the app work under a path prefix without hardcoding it.

    Two sources, in priority order:

    1. ``X-Forwarded-Prefix`` — set by a reverse proxy (nginx/caddy/ingress)
       that strips the prefix before forwarding. The path is already clean, so
       we only need to teach ``reverse()`` / ``{% url %}`` to re-add it.
    2. An ``/absproxy/<port>/`` (or ``/proxy/<port>/``) prefix embedded in the
       path — how code-server / VS Code forward a local port. Here the prefix
       arrives as part of the path, so we both strip it for URL resolution and
       set it as the script prefix for link generation.

    No prefix from either source → no change, so direct access is unaffected.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        prefix = request.META.get("HTTP_X_FORWARDED_PREFIX", "").strip()
        strip_from_path = False

        if not prefix:
            match = _ABSPROXY_PREFIX.match(request.path_info or "")
            if match:
                prefix = match.group(0)
                strip_from_path = True

        if prefix:
            prefix = "/" + prefix.strip("/")
            request.META["SCRIPT_NAME"] = prefix
            set_script_prefix(prefix + "/")

            if strip_from_path and request.path_info.startswith(prefix):
                # Expose the clean path to the URL resolver (which reads
                # request.path_info) so /absproxy/8011/discover/ resolves as
                # /discover/. Keep request.path consistent for redirects/logs.
                request.path_info = request.path_info[len(prefix):] or "/"
                request.path = prefix + request.path_info

        return self.get_response(request)
