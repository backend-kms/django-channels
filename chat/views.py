# chat/views.py
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


def index(request):
    return render(request, "chat/index.html")

def room(request, room_name):
    return render(request, "chat/room.html", {"room_name": room_name})

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


# 기존 템플릿 뷰들 (테스트용으로 유지)
def index(request):
    return render(request, "chat/index.html")

def room(request, room_name):
    return render(request, "chat/room.html", {"room_name": room_name})


class RoomListAPIView(APIView):
    """채팅방 목록 조회 API"""
    
    def get(self, request):
        """활성화된 공개 채팅방 목록 반환"""
        try:
            # 쿼리 파라미터 처리
            page = int(request.GET.get('page', 1))
            limit = min(int(request.GET.get('limit', 20)), 100)  # 최대 100개
            search = request.GET.get('search', '').strip()
            sort_by = request.GET.get('sort', 'popularity')  # popularity, name, recent
            
            # 기본 쿼리셋
            queryset = ChatRoom.objects.filter(
                is_active=True,
                is_private=False
            ).annotate(
                online_members=Count(
                    'members',
                    filter=Q(members__is_online=True)
                ),
                total_members=Count('members'),
                message_count=Count('messages', filter=Q(messages__is_deleted=False))
            )
            
            # 검색 필터
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | 
                    Q(description__icontains=search)
                )
            
            # 정렬
            if sort_by == 'popularity':
                queryset = queryset.order_by('-online_members', '-total_members')
            elif sort_by == 'name':
                queryset = queryset.order_by('name')
            elif sort_by == 'recent':
                queryset = queryset.order_by('-created_at')
            else:
                queryset = queryset.order_by('-online_members')
            
            # 페이지네이션
            start = (page - 1) * limit
            end = start + limit
            total_count = queryset.count()
            rooms = queryset[start:end]
            
            # 데이터 직렬화
            rooms_data = []
            for room in rooms:
                rooms_data.append({
                    'id': room.id,
                    'name': room.name,
                    'description': room.description,
                    'online_members': room.online_members,
                    'total_members': room.total_members,
                    'message_count': room.message_count,
                    'max_members': room.max_members,
                    'created_at': room.created_at.isoformat(),
                    'is_full': room.online_members >= room.max_members,
                    'websocket_url': f'ws://localhost:8000/ws/chat/{room.name}/',
                })
            
            return Response({
                'success': True,
                'data': {
                    'rooms': rooms_data,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total_count,
                        'has_next': end < total_count,
                        'has_prev': page > 1
                    }
                },
                'websocket_base_url': 'ws://localhost:8000/ws/chat/'
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': '잘못된 페이지 또는 limit 값입니다.',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': '채팅방 목록을 가져오는데 실패했습니다.',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoomDetailAPIView(APIView):
    """특정 채팅방 상세 정보 조회/생성 API"""
    
    def get(self, request, room_name):
        """채팅방 상세 정보 및 최근 메시지 반환"""
        try:
            # 채팅방 조회 또는 생성
            room, created = ChatRoom.objects.get_or_create(
                name=room_name,
                defaults={
                    'description': f'{room_name} 채팅방',
                    'created_by': None,  # 익명 사용자
                }
            )
            
            # 채팅방이 비활성화된 경우
            if not room.is_active:
                return Response({
                    'success': False,
                    'error': '비활성화된 채팅방입니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 최근 메시지들 가져오기
            message_limit = int(request.GET.get('message_limit', 50))
            recent_messages = ChatMessage.objects.filter(
                room=room,
                is_deleted=False
            ).select_related('user').order_by('-created_at')[:message_limit]
            
            # 메시지 데이터 직렬화
            messages_data = []
            for msg in reversed(recent_messages):
                messages_data.append({
                    'id': msg.id,
                    'content': msg.content,
                    'author': msg.author_name,
                    'message_type': msg.message_type,
                    'created_at': msg.created_at.isoformat(),
                    'reply_to': msg.reply_to.id if msg.reply_to else None,
                    'file_url': msg.file_url if msg.file_url else None,
                })
            
            # 온라인 멤버 수 계산
            online_members = RoomMember.objects.filter(
                room=room,
                is_online=True
            ).count()
            
            # 방 설정 가져오기
            try:
                room_settings = room.settings
            except ChatRoomSettings.DoesNotExist:
                # 기본 설정 생성
                room_settings = ChatRoomSettings.objects.create(room=room)
            
            room_data = {
                'id': room.id,
                'name': room.name,
                'description': room.description,
                'websocket_url': f'ws://localhost:8000/ws/chat/{room_name}/',
                'online_members': online_members,
                'max_members': room.max_members,
                'total_messages': room.total_messages,
                'created_at': room.created_at.isoformat(),
                'is_active': room.is_active,
                'is_private': room.is_private,
                'is_full': online_members >= room.max_members,
                'was_created': created,
                'recent_messages': messages_data,
                'settings': {
                    'allow_file_upload': room_settings.allow_file_upload,
                    'allow_image_upload': room_settings.allow_image_upload,
                    'slow_mode_seconds': room_settings.slow_mode_seconds,
                    'welcome_message': room_settings.welcome_message,
                }
            }
            
            return Response({
                'success': True,
                'data': room_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'채팅방 {room_name} 정보를 가져오는데 실패했습니다.',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoomValidationAPIView(APIView):
    """채팅방 이름 유효성 검사 및 입장 가능 여부 확인"""
    
    def post(self, request):
        """방 이름 유효성 검사 및 입장 준비"""
        try:
            room_name = request.data.get('room_name', '').strip()
            
            # 기본 유효성 검사
            validation_result = self._validate_room_name(room_name)
            if not validation_result['is_valid']:
                return Response({
                    'success': False,
                    'error': validation_result['error']
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 기존 방 확인
            try:
                room = ChatRoom.objects.get(name=room_name)
                
                # 방 상태 검사
                if not room.is_active:
                    return Response({
                        'success': False,
                        'error': '비활성화된 채팅방입니다.'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # 인원 제한 검사
                current_members = RoomMember.objects.filter(
                    room=room,
                    is_online=True
                ).count()
                
                if current_members >= room.max_members:
                    return Response({
                        'success': False,
                        'error': f'채팅방이 가득 찼습니다. (최대 {room.max_members}명)'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # 비밀번호 보호 방 검사
                if room.is_private and room.password:
                    provided_password = request.data.get('password', '')
                    if provided_password != room.password:
                        return Response({
                            'success': False,
                            'error': '올바른 비밀번호를 입력해주세요.',
                            'requires_password': True
                        }, status=status.HTTP_401_UNAUTHORIZED)
                
                message = f'기존 {room_name} 채팅방에 입장합니다.'
                
            except ChatRoom.DoesNotExist:
                message = f'새로운 {room_name} 채팅방을 생성합니다.'
            
            return Response({
                'success': True,
                'data': {
                    'room_name': room_name,
                    'websocket_url': f'ws://localhost:8000/ws/chat/{room_name}/',
                    'message': message,
                    'can_join': True
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': '방 입장 검증에 실패했습니다.',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_room_name(self, room_name):
        """방 이름 유효성 검사 헬퍼 메서드"""
        if not room_name:
            return {'is_valid': False, 'error': '방 이름을 입력해주세요.'}
        
        if len(room_name) < 2:
            return {'is_valid': False, 'error': '방 이름은 2자 이상이어야 합니다.'}
        
        if len(room_name) > 50:
            return {'is_valid': False, 'error': '방 이름은 50자 이하여야 합니다.'}
        
        # 특수문자 검사 (영문, 숫자, 한글, 하이픈, 언더스코어만 허용)
        if not re.match(r'^[a-zA-Z0-9가-힣_-]+$', room_name):
            return {'is_valid': False, 'error': '방 이름에는 영문, 숫자, 한글, -, _ 만 사용 가능합니다.'}
        
        # 금지된 단어 검사 (필요시 추가)
        forbidden_words = ['admin', 'system', 'test', 'null', 'undefined']
        if room_name.lower() in forbidden_words:
            return {'is_valid': False, 'error': '사용할 수 없는 방 이름입니다.'}
        
        return {'is_valid': True, 'error': None}


class RoomStatsAPIView(APIView):
    """채팅방 및 서버 통계 정보 API"""
    
    def get(self, request):
        """실시간 통계 정보 반환"""
        try:
            # 기본 통계
            total_rooms = ChatRoom.objects.filter(is_active=True).count()
            total_users = User.objects.filter(is_active=True).count()
            
            # 온라인 사용자 수
            online_users = UserProfile.objects.filter(is_online=True).count()
            
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
            
            # 가장 인기있는 방 (온라인 멤버 기준)
            popular_room = ChatRoom.objects.filter(
                is_active=True
            ).annotate(
                online_count=Count(
                    'members',
                    filter=Q(members__is_online=True)
                )
            ).order_by('-online_count').first()
            
            # 오늘 가장 활발한 방 (메시지 수 기준)
            active_room = ChatRoom.objects.annotate(
                today_messages=Count(
                    'messages',
                    filter=Q(
                        messages__created_at__date=today,
                        messages__is_deleted=False
                    )
                )
            ).order_by('-today_messages').first()
            
            stats_data = {
                'server': {
                    'total_rooms': total_rooms,
                    'total_users': total_users,
                    'online_users': online_users,
                    'total_messages_today': today_messages,
                    'new_users_this_week': new_users_this_week,
                    'online_percentage': round((online_users / total_users * 100) if total_users > 0 else 0, 1),
                    'server_status': 'healthy'
                },
                'popular_rooms': {
                    'most_popular': {
                        'name': popular_room.name if popular_room else None,
                        'online_members': popular_room.online_count if popular_room else 0
                    },
                    'most_active_today': {
                        'name': active_room.name if active_room else None,
                        'messages_today': active_room.today_messages if active_room else 0
                    }
                }
            }
            
            return Response({
                'success': True,
                'data': stats_data,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': '통계 정보를 가져오는데 실패했습니다.',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoomCreateAPIView(APIView):
    """새 채팅방 생성 API"""
    
    def post(self, request):
        """새 채팅방 생성"""
        try:
            data = request.data
            room_name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            max_members = data.get('max_members', 100)
            is_private = data.get('is_private', False)
            password = data.get('password', '').strip() if is_private else ''
            
            # 방 이름 유효성 검사
            validation_result = RoomValidationAPIView()._validate_room_name(room_name)
            if not validation_result['is_valid']:
                return Response({
                    'success': False,
                    'error': validation_result['error']
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
                is_private=is_private,
                password=password,
                created_by=None  # 익명 사용자
            )
            
            # 기본 설정 생성
            ChatRoomSettings.objects.create(
                room=room,
                welcome_message=f'{room_name} 채팅방에 오신 것을 환영합니다!',
            )
            
            return Response({
                'success': True,
                'data': {
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
                'error': '채팅방 생성에 실패했습니다.',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)