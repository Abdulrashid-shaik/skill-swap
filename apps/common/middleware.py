import re

from django.conf import settings
from django.urls import set_script_prefix

# code-server (and VS Code) expose a local port at ``/absproxy/<port>/`` and
# forward the FULL path through (unlike ``/proxy/<port>/``, which strips it but
# tells the backend nothing). We detect that prefix from the path itself.
_ABSPROXY_PREFIX = re.compile(r"^/(?:abs)?proxy/\d+")


class ForwardedPrefixMiddleware:
    """Make the app work under a path prefix without hardcoding it.

    Three sources, in priority order:

    1. ``settings.APP_URL_PREFIX`` — an explicit, operator-configured prefix for
       proxies that strip the sub-path *and* send no header (e.g. code-server's
       ``/proxy/<port>/``). The app cannot otherwise discover it. The inbound
       path may already be clean (proxy stripped it) or still carry the prefix,
       so we strip it only when present.
    2. ``X-Forwarded-Prefix`` — set by a reverse proxy (nginx/caddy/ingress)
       that strips the prefix before forwarding. The path is already clean, so
       we only need to teach ``reverse()`` / ``{% url %}`` to re-add it.
    3. An ``/absproxy/<port>/`` (or ``/proxy/<port>/``) prefix embedded in the
       path — how code-server / VS Code forward a local port. Here the prefix
       arrives as part of the path, so we both strip it for URL resolution and
       set it as the script prefix for link generation.

    No prefix from any source → no change, so direct access is unaffected.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        strip_from_path = False

        prefix = (getattr(settings, "APP_URL_PREFIX", "") or "").strip()
        if prefix:
            # Explicitly configured: prefix every generated URL. Strip it from
            # the path only if the proxy forwarded it (it usually won't).
            strip_from_path = (request.path_info or "").startswith(prefix)
        else:
            prefix = request.META.get("HTTP_X_FORWARDED_PREFIX", "").strip()
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
                # /discover/.
                request.path_info = request.path_info[len(prefix):] or "/"

            # Mirror a real SCRIPT_NAME mount: request.path carries the prefix so
            # request.get_full_path() — hence the ?next= login redirect, logs and
            # any path-based links — stays inside the proxy mount.
            request.path = prefix + request.path_info

        return self.get_response(request)
