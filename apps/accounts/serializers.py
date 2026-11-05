from rest_framework import serializers

from .models import UserProfile


class ProfileSerializer(serializers.ModelSerializer):
    """Read-only public view of a member's profile. Profile *editing* stays in
    the template settings form (no PATCH endpoint is exposed)."""

    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "user_id", "email", "username", "full_name", "bio", "location",
            "experience_level", "avatar", "rating_avg", "rating_count",
            "completed_exchanges",
        ]
        read_only_fields = fields
