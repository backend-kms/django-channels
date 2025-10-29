from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import ChatRoom, RoomMember, ChatMessage, UserProfile, ChatRoomSettings
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
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
            # 활성화된 채팅방들 가져오기
            rooms = ChatRoom.objects.filter(is_active=True).annotate(
                member_count=Count('members', filter=Q(members__is_online=True))
            )[:20]
            
            rooms_data = []
            for room in rooms:
                rooms_data.append({
                    'id': room.id,
                    'name': room.name,
                    'description': room.description,
                    'created_at': room.created_at.isoformat(),
                    'member_count': room.member_count,
                    'max_members': room.max_members,
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


class RoomDetailAPIView(APIView):
    """채팅방 상세 정보"""
    
    def get(self, request, room_name):
        try:
            # 채팅방 조회 또는 생성
            room, created = ChatRoom.objects.get_or_create(
                name=room_name,
                defaults={'description': f'{room_name} 채팅방'}
            )
            
            # 최근 메시지들 가져오기 (최대 50개)
            recent_messages = ChatMessage.objects.filter(
                room=room,
                is_deleted=False
            ).order_by('-created_at')[:50]
            
            messages_data = []
            for msg in reversed(recent_messages):
                messages_data.append({
                    'id': msg.id,
                    'content': msg.content,
                    'author': msg.author_name,
                    'created_at': msg.created_at.isoformat(),
                })
            
            return Response({
                'success': True,
                'room': {
                    'id': room.id,
                    'name': room.name,
                    'description': room.description,
                    'websocket_url': f'ws://localhost:8000/ws/chat/{room_name}/',
                    'was_created': created,
                    'recent_messages': messages_data,
                },
                'message': '채팅방 정보를 가져왔습니다.'
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
            
            if len(room_name) < 2:
                return Response({
                    'success': False,
                    'error': '방 이름은 2자 이상이어야 합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if len(room_name) > 50:
                return Response({
                    'success': False,
                    'error': '방 이름은 50자 이하여야 합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 특수문자 검사
            if not re.match(r'^[a-zA-Z0-9가-힣_-]+$', room_name):
                return Response({
                    'success': False,
                    'error': '방 이름에는 영문, 숫자, 한글, -, _ 만 사용 가능합니다.'
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


class RoomCreateAPIView(APIView):
    """새 채팅방 생성 API"""
    
    def post(self, request):
        try:
            room_name = request.data.get('name', '').strip()
            description = request.data.get('description', '').strip()
            max_members = request.data.get('max_members', 100)
            
            # 기본 유효성 검사
            if not room_name:
                return Response({
                    'success': False,
                    'error': '방 이름을 입력해주세요.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 중복 확인
            if ChatRoom.objects.filter(name=room_name).exists():
                return Response({
                    'success': False,
                    'error': '이미 존재하는 방 이름입니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 방 생성
            room = ChatRoom.objects.create(
                name=room_name,
                description=description or f'{room_name} 채팅방',
                max_members=max_members,
            )
            
            return Response({
                'success': True,
                'room': {
                    'id': room.id,
                    'name': room.name,
                    'description': room.description,
                    'websocket_url': f'ws://localhost:8000/ws/chat/{room_name}/',
                    'created_at': room.created_at.isoformat(),
                },
                'message': f'{room_name} 채팅방이 성공적으로 생성되었습니다.'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoomStatsAPIView(APIView):
    """채팅방 및 서버 통계 정보 API"""
    
    def get(self, request):
        try:
            # 기본 통계
            total_rooms = ChatRoom.objects.filter(is_active=True).count()
            total_users = User.objects.count()
            
            # 오늘 생성된 메시지 수
            today = timezone.now().date()
            today_messages = ChatMessage.objects.filter(
                created_at__date=today,
                is_deleted=False
            ).count()
            
            # 이번 주 새로운 사용자
            week_ago = timezone.now() - timedelta(days=7)
            new_users_this_week = User.objects.filter(
                date_joined__gte=week_ago
            ).count()
            
            # 온라인 사용자 (UserProfile이 있으면)
            try:
                online_users = UserProfile.objects.filter(is_online=True).count()
            except:
                online_users = 0
            
            stats_data = {
                'total_rooms': total_rooms,
                'total_users': total_users,
                'online_users': online_users,
                'today_messages': today_messages,
                'new_users_this_week': new_users_this_week,
                'server_status': 'healthy'
            }
            
            return Response({
                'success': True,
                'stats': stats_data,
                'message': '통계 정보를 가져왔습니다.',
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)