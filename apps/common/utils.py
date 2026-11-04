from django.utils.text import slugify


def unique_slugify(instance, value, field_name="slug", max_base_length=110):
    """Return a slug unique for instance's model, deriving it from value.

    Appends -2, -3, ... on collision. Excludes the instance's own row so
    re-saving is stable.
    """
    base = slugify(value)[:max_base_length] or "item"
    slug = base
    model = instance.__class__
    qs = model._default_manager.all()
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    n = 1
    while qs.filter(**{field_name: slug}).exists():
        n += 1
        slug = f"{base}-{n}"
    return slug
