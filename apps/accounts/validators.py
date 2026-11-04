from django.core.exceptions import ValidationError

MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB


def validate_avatar_size(f):
    """Reject avatars larger than 2 MB. Image-type validity is enforced by
    ImageField/forms.ImageField (Pillow) and the extension validator."""
    if f.size and f.size > MAX_AVATAR_BYTES:
        raise ValidationError("Image file too large — maximum size is 2 MB.")
