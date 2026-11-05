from rest_framework import serializers

from .models import Skill, SkillKind, SkillStatus, UserSkill


class SkillSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="name", read_only=True)
    category_slug = serializers.SlugRelatedField(
        source="category", slug_field="slug", read_only=True
    )

    class Meta:
        model = Skill
        fields = ["id", "name", "slug", "category", "category_slug", "description"]
        read_only_fields = fields


class UserSkillSerializer(serializers.ModelSerializer):
    skill = SkillSerializer(read_only=True)
    skill_id = serializers.PrimaryKeyRelatedField(
        source="skill", queryset=Skill.objects.all(), write_only=True
    )

    class Meta:
        model = UserSkill
        fields = ["id", "skill", "skill_id", "kind", "proficiency", "note", "is_active"]
        read_only_fields = ["id", "is_active"]

    def validate_skill_id(self, skill):
        # Only approved, active catalogue entries may be added.
        if not skill.is_available:
            raise serializers.ValidationError("That skill is not available.")
        return skill

    def validate(self, attrs):
        user = self.context["request"].user
        skill = attrs.get("skill")
        kind = attrs.get("kind")
        if UserSkill.objects.filter(user=user, skill=skill, kind=kind).exists():
            raise serializers.ValidationError("That skill is already in this list.")
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
