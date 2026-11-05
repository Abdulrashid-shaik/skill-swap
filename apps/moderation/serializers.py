from rest_framework import serializers

from .models import ReportReason


class ReportCreateSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=ReportReason.choices)
    description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
