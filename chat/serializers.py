from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate, login
from django.utils import timezone

from chat.models import ChatMessage, MessageReaction, PushSubscription


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    access_token = serializers.CharField(required=False)
    refresh_token = serializers.CharField(required=False)
    user = serializers.DictField(required=False)
    message = serializers.CharField(required=False)
    error = serializers.CharField(required=False)


class ChatMessageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username")
    user_id = serializers.IntegerField(source="user.id")
    room_name = serializers.CharField(source="room.name")
    reactions=serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "room_name",
            "user_id",
            "username",
            "content",
            "file",
            "file_name",
            "file_size",
            "message_type",
            "created_at",
            "edited_at",
            "reactions",
            "unread_count",
            "is_read_by_all",
        ]
    
    def get_reactions(self, obj):
        # 각 반응별 개수 집계
        reaction_counts = {
            "like": 0,
            "good": 0,
            "check": 0,
        }
        reactions = MessageReaction.objects.filter(message=obj)
        for r in reactions:
            if r.reaction_type in reaction_counts:
                reaction_counts[r.reaction_type] += 1
        return reaction_counts
class PushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ['id', 'user', 'endpoint', 'p256dh', 'auth', 'created_at']