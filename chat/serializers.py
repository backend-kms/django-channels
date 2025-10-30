from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate, login
from django.utils import timezone

from chat.models import ChatMessage

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
    username = serializers.CharField(source='user.username')
    room_name = serializers.CharField(source='room.name')
    class Meta:
        model = ChatMessage
        fields = ['id', 'room_name', 'username', 'content', 'message_type', 'created_at', 'edited_at']