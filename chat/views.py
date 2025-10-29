from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import ChatRoom, RoomMember, ChatMessage, UserProfile, ChatRoomSettings
from django.db.models import Count, Q
from django.utils import timezone
import re


# 기존 템플릿 뷰들 (테스트용)
def index(request):
    return render(request, "chat/index.html")

def room(request, room_name):
    return render(request, "chat/room.html", {"room_name": room_name})


class RoomListAPIView(APIView):
    """채팅방 목록 조회 API"""
    
    def get(self, request):
        try:
            # 간단한 채팅방 목록 반환
            rooms = ChatRoom.objects.filter(is_active=True)[:10]
            
            rooms_data = []
            for room in rooms:
                rooms_data.append({
                    'id': room.id,
                    'name': room.name,
                    'description': room.description,
                    'created_at': room.created_at.isoformat(),
                })
            
            return Response({
                'success': True,
                'rooms': rooms_data,
                'message': '채팅방 목록을 성공적으로 가져왔습니다.'
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoomValidationAPIView(APIView):
    """방 이름 유효성 검사"""
    
    def post(self, request):
        try:
            room_name = request.data.get('room_name', '').strip()
            
            if not room_name:
                return Response({
                    'success': False,
                    'error': '방 이름을 입력해주세요.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'room_name': room_name,
                'websocket_url': f'ws://localhost:8000/ws/chat/{room_name}/',
                'message': f'{room_name} 방에 입장할 수 있습니다.'
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoomDetailAPIView(APIView):
    """채팅방 상세 정보"""
    
    def get(self, request, room_name):
        try:
            # 채팅방 조회 또는 생성
            room, created = ChatRoom.objects.get_or_create(
                name=room_name,
                defaults={'description': f'{room_name} 채팅방'}
            )
            
            return Response({
                'success': True,
                'room': {
                    'id': room.id,
                    'name': room.name,
                    'description': room.description,
                    'websocket_url': f'ws://localhost:8000/ws/chat/{room_name}/',
                    'was_created': created,
                },
                'message': '채팅방 정보를 가져왔습니다.'
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)