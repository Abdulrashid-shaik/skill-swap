from django.core.files.storage import FileSystemStorage
from django.urls import get_script_prefix


class ProxyAwareMediaStorage(FileSystemStorage):
    """FileSystemStorage whose URLs honor the active script prefix.

    Behind a path-prefix proxy (e.g. code-server's ``/absproxy/<port>/``),
    ``ForwardedPrefixMiddleware`` sets the request's script prefix. A
    root-absolute media URL like ``/media/avatars/x.png`` would escape that
    prefix and 404, so uploaded images (profile avatars) would not load.
    Prepending the active prefix keeps them loading behind the proxy; on direct
    access the prefix is just ``/`` and the URL is returned unchanged.
    """

    def url(self, name):
        url = super().url(name)
        prefix = get_script_prefix().rstrip("/")
        if prefix and url.startswith("/"):
            return prefix + url
        return url
