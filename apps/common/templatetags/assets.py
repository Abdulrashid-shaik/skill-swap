"""Inline the design-system CSS into the page.

Embedding the stylesheet in the HTML (rather than linking separate /static/
files) makes styling load reliably behind path-rewriting dev proxies, where
asset requests to /static/... may not reach the app. The CSS source of truth
remains the files under static/css/. The payload is tiny (~2 KB).
"""
from pathlib import Path

from django.conf import settings
from django.template import Library
from django.utils.safestring import mark_safe

register = Library()

# Order matters: variables first, then everything that references them.
CSS_FILES = [
    "_variables.css",
    "_base.css",
    "_typography.css",
    "_layout.css",
    "_components.css",
    "_buttons.css",
    "_forms.css",
]


@register.simple_tag
def inline_css():
    css_dir = Path(settings.BASE_DIR) / "static" / "css"
    parts = []
    for name in CSS_FILES:
        path = css_dir / name
        if path.exists():
            parts.append(path.read_text())
    return mark_safe("<style>\n" + "\n".join(parts) + "\n</style>")
