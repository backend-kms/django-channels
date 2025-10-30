from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from chat.serializers import LoginRequestSerializer, LoginResponseSerializer
from .models import ChatRoom, ChatMessage, UserProfile
from django.utils import timezone
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema


# 기존 템플릿 뷰들 (테스트용)
def index(request):
    return render(request, "chat/index.html")

def room(request, room_name):
    return render(request, "chat/room.html", {"room_name": room_name})

# ========== 인증 관련 API ==========

class LoginAPIView(APIView):
    """JWT 기반 로그인 API"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer, 401: LoginResponseSerializer},
        description="JWT 토큰 기반 로그인. access_token과 refresh_token을 반환합니다."
    )
    def post(self, request):
        try:
            serializer = LoginRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            user = authenticate(username=data['username'], password=data['password'])
            
            if user:
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'is_online': True, 'last_activity': timezone.now()}
                )
                if not created:
                    profile.is_online = True
                    profile.last_activity = timezone.now()
                    profile.save()
                                
                return Response({
                    'success': True,
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email
                    },
                    'message': f"{user.username}님, 환영합니다!"
                })
            else:
                return Response({
                    'success': False,
                    'error': "아이디 또는 비밀번호가 틀렸습니다."
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except Exception as e:
            print(f"❌ 로그인 오류: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutAPIView(APIView):
    """로그아웃 API"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            try:
                profile = UserProfile.objects.get(user=request.user)
                profile.is_online = False
                profile.last_activity = timezone.now()
                profile.save()
            except UserProfile.DoesNotExist:
                pass
            
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except:
                    pass
                        
            return Response({
                'success': True,
                'message': '로그아웃되었습니다.'
            })
                
        except Exception as e:
            print(f"❌ 로그아웃 오류: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileAPIView(APIView):
    """현재 사용자 정보 조회 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            
            return Response({
                'result': {
                    "id": request.user.id,
                    "username": request.user.username,
                    "avatar": profile.avatar.url if profile.avatar else None,
                    "bio": profile.bio,
                    "is_online": profile.is_online,
                    "last_activity": profile.last_activity,
                    "preferred_language": profile.preferred_language,
                }
            })
                
        except Exception as e:
            print(f"❌ 프로필 조회 오류: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========== 채팅방 관련 API ==========

class RoomListAPIView(APIView):
    """채팅방 목록 조회 API"""
    
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            rooms = ChatRoom.objects.filter(is_active=True).select_related('created_by')[:20]

            rooms_data = []
            for room in rooms:
                can_delete = False
                if request.user.is_authenticated and room.created_by:
                    can_delete = (room.created_by == request.user)
                    print(f"🗑️ 방 '{room.name}': can_delete={can_delete} (생성자: {room.created_by.username}, 현재: {request.user.username})")
                
                rooms_data.append({
                    'id': room.id,
                    'name': room.name,
                    'description': room.description,
                    'created_at': room.created_at.isoformat(),
                    'created_by': room.created_by.username if room.created_by else '알 수 없음',
                    'member_count': room.current_member_count,
                    'max_members': room.max_members,
                    'can_delete': can_delete,
                })
            
            print(f"✅ 총 {len(rooms_data)}개 방 반환, 인증상태: {request.user.is_authenticated}")
            
            return Response({
                'results': rooms_data
            })

        except Exception as e:
            print(f"❌ 방 목록 오류: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RoomCreateAPIView(APIView):
    """새 채팅방 생성 API"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            room_name = request.data.get('name', '').strip()
            description = request.data.get('description', '').strip()
            max_members_input = request.data.get('max_members', 100)
            
            # max_members 정수 변환 처리
            try:
                if isinstance(max_members_input, str):
                    max_members = int(max_members_input) if max_members_input.strip() else 100
                else:
                    max_members = int(max_members_input)
            except (ValueError, TypeError):
                max_members = 100
            
            # 범위 제한
            max_members = max(1, min(max_members, 1000))
            
            if not room_name:
                return Response({
                    'success': False,
                    'error': '방 이름을 입력해주세요.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if ChatRoom.objects.filter(name=room_name, is_active=True).exists():
                return Response({
                    'success': False,
                    'error': '이미 존재하는 방 이름입니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            room = ChatRoom.objects.create(
                name=room_name,
                description=description or f'{room_name} 채팅방',
                max_members=max_members,
                created_by=request.user,
            )
            
            print(f"✅ 방 생성 완료: {room.name}, 생성자: {room.created_by.username}, 최대인원: {max_members}")
            
            return Response({
                'success': True,
                'room': {
                    'id': room.id,
                    'name': room.name,
                    'description': room.description,
                    'created_at': room.created_at.isoformat(),
                    'created_by': room.created_by.username,
                    'max_members': room.max_members,
                    'can_delete': True,
                },
                'message': f'{room_name} 채팅방이 성공적으로 생성되었습니다.'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ 방 생성 오류: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoomDeleteAPIView(APIView):
    """채팅방 삭제 API"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, room_id):
        try:
            try:
                room = ChatRoom.objects.get(id=room_id, is_active=True)
            except ChatRoom.DoesNotExist:
                return Response({
                    'success': False,
                    'error': '존재하지 않는 채팅방입니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            if room.created_by != request.user:
                return Response({
                    'success': False,
                    'error': '채팅방을 삭제할 권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            room_name = room.name
            room.is_active = False
            room.save()
            
            print(f"🗑️ {request.user.username}님이 '{room_name}' 방을 삭제했습니다.")
            
            return Response({
                'success': True,
                'message': f'{room_name} 채팅방이 삭제되었습니다.'
            })
            
        except Exception as e:
            print(f"❌ 방 삭제 오류: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RoomDetailAPIView(APIView):
    """채팅방 상세 정보"""
    permission_classes = [AllowAny]
    
    def get(self, request, room_name):
        try:
            room, created = ChatRoom.objects.get_or_create(
                name=room_name,
                defaults={
                    'description': f'{room_name} 채팅방',
                    'created_by': request.user if request.user.is_authenticated else None
                }
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
            print(f"❌ 방 상세 정보 오류: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RoomStatsAPIView(APIView):
    """서버 통계 API"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            total_rooms = ChatRoom.objects.filter(is_active=True).count()
            total_users = User.objects.count()
            
            today = timezone.now().date()
            today_messages = ChatMessage.objects.filter(
                created_at__date=today,
                is_deleted=False
            ).count()
            
            try:
                online_users = UserProfile.objects.filter(is_online=True).count()
            except:
                online_users = 0
            
            return Response({
                'success': True,
                'stats': {
                    'total_rooms': total_rooms,
                    'total_users': total_users,
                    'online_users': online_users,
                    'today_messages': today_messages,
                    'server_status': 'healthy'
                },
                'message': '통계 정보를 가져왔습니다.'
            })
            
        except Exception as e:
            print(f"❌ 통계 오류: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)