from rest_framework import serializers

from .models import Exchange, ExchangeRequest


def _person(user):
    return {"id": user.pk, "name": user.profile.full_name or user.email}


class ExchangeRequestSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    receiver = serializers.SerializerMethodField()
    offered_skill = serializers.StringRelatedField()
    requested_skill = serializers.StringRelatedField()

    class Meta:
        model = ExchangeRequest
        fields = [
            "id", "sender", "receiver", "offered_skill", "requested_skill",
            "message", "status", "created_at", "responded_at",
        ]
        read_only_fields = fields

    def get_sender(self, obj):
        return _person(obj.sender)

    def get_receiver(self, obj):
        return _person(obj.receiver)


class ExchangeRequestCreateSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField()
    offered_skill_id = serializers.IntegerField()
    requested_skill_id = serializers.IntegerField()
    message = serializers.CharField(required=False, allow_blank=True, default="")


class ExchangeSerializer(serializers.ModelSerializer):
    participant_a = serializers.SerializerMethodField()
    participant_b = serializers.SerializerMethodField()
    skill_a_teaches = serializers.StringRelatedField()
    skill_b_teaches = serializers.StringRelatedField()
    i_confirmed = serializers.SerializerMethodField()

    class Meta:
        model = Exchange
        fields = [
            "id", "participant_a", "participant_b", "skill_a_teaches",
            "skill_b_teaches", "status", "started_at", "completed_at",
            "cancelled_at", "i_confirmed",
        ]
        read_only_fields = fields

    def get_participant_a(self, obj):
        return _person(obj.participant_a)

    def get_participant_b(self, obj):
        return _person(obj.participant_b)

    def get_i_confirmed(self, obj):
        user = self.context["request"].user
        return obj.has_confirmed(user)
