from datetime import datetime
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from chat.serializers import (
    ChatMessageSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
)
from .models import ChatRoom, ChatMessage, RoomMember, UserProfile
from django.utils import timezone
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema


# 기존 템플릿 뷰들 (테스트용)
def index(request):
    return render(request, "chat/index.html")

def room(request, room_name):
    return render(request, "chat/room.html", {"room_name": room_name})


# 인증 관련 API
class LoginAPIView(APIView):
    """
    JWT 기반 로그인 API
    사용자 인증 후 access_token과 refresh_token 반환, 온라인 상태 업데이트
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer, 401: LoginResponseSerializer},
        description="JWT 토큰 기반 로그인. access_token과 refresh_token을 반환합니다.",
    )
    def post(self, request):
        try:
            serializer = LoginRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            user = authenticate(username=data["username"], password=data["password"])

            if user:
                # JWT 토큰 생성
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)

                # 사용자 프로필 온라인 상태 업데이트
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={"is_online": True, "last_activity": timezone.now()},
                )
                if not created:
                    profile.is_online = True
                    profile.last_activity = timezone.now()
                    profile.save()

                return Response({
                    "success": True,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                    },
                    "message": f"{user.username}님, 환영합니다!",
                })
            else:
                return Response(
                    {"success": False, "error": "아이디 또는 비밀번호가 틀렸습니다."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except Exception as e:
            print(f"❌ 로그인 오류: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutAPIView(APIView):
    """
    로그아웃 API
    사용자 오프라인 상태 변경 후 refresh_token 블랙리스트 처리
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # 사용자 오프라인 상태 변경
            try:
                profile = UserProfile.objects.get(user=request.user)
                profile.is_online = False
                profile.last_activity = timezone.now()
                profile.save()
            except UserProfile.DoesNotExist:
                pass

            # 리프레시 토큰 블랙리스트 처리
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except:
                    pass

            return Response({"success": True, "message": "로그아웃되었습니다."})

        except Exception as e:
            print(f"❌ 로그아웃 오류: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserProfileAPIView(APIView):
    """
    현재 사용자 정보 조회 API
    인증된 사용자의 프로필 정보 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)

            return Response({
                "result": {
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
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# 채팅방 관련 API
class RoomListAPIView(APIView):
    """
    채팅방 목록 조회 API
    활성화된 모든 채팅방 목록 반환 (본인이 속한 방 제외)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # 본인이 속한 방 제외
            rooms_in_me = (
                RoomMember.objects.filter(
                    user=request.user, room__is_active=True
                ).values_list("room_id", flat=True)
                if request.user.is_authenticated
                else []
            )
            
            rooms = (
                ChatRoom.objects.filter(is_active=True)
                .exclude(id__in=rooms_in_me)
                .select_related("created_by")[:20]
            )

            rooms_data = []
            for room in rooms:
                can_delete = False
                if request.user.is_authenticated and room.created_by:
                    can_delete = room.created_by == request.user

                rooms_data.append({
                    "id": room.id,
                    "name": room.name,
                    "description": room.description,
                    "created_at": room.created_at.isoformat(),
                    "created_by": (
                        room.created_by.username
                        if room.created_by
                        else "알 수 없음"
                    ),
                    "max_members": room.max_members,
                    "member_count": RoomMember.objects.filter(room=room).count(),
                    "can_delete": can_delete,
                })

            return Response({"results": rooms_data})

        except Exception as e:
            print(f"❌ 방 목록 오류: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MyRoomsAPIView(APIView):
    """
    내가 속한 채팅방 목록 조회 API
    현재 사용자가 멤버로 등록된 모든 활성 방 목록 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            my_memberships = (
                RoomMember.objects.filter(user=request.user, room__is_active=True)
                .select_related("room", "room__created_by")
                .order_by("-last_seen")
            )

            rooms_data = []
            for membership in my_memberships:
                room = membership.room
                current_member_count = RoomMember.objects.filter(room=room).count()

                rooms_data.append({
                    "id": room.id,
                    "name": room.name,
                    "description": room.description,
                    "created_at": room.created_at.isoformat(),
                    "created_by": (
                        room.created_by.username
                        if room.created_by
                        else "알 수 없음"
                    ),
                    "max_members": room.max_members,
                    "member_count": current_member_count,
                    "is_admin": membership.is_admin,
                    "last_seen": (
                        membership.last_seen.isoformat()
                        if membership.last_seen
                        else None
                    ),
                    "joined_at": (
                        membership.joined_at.isoformat()
                        if membership.joined_at
                        else None
                    ),
                })

            return Response(rooms_data)

        except Exception as e:
            print(f"❌ 내 방 목록 오류: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RoomCreateAPIView(APIView):
    """
    새 채팅방 생성 API
    새로운 채팅방 생성 후 생성자를 관리자로 자동 등록
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            room_name = request.data.get("name", "").strip()
            description = request.data.get("description", "").strip()
            max_members_input = request.data.get("max_members", 100)

            # max_members 정수 변환 및 범위 제한
            try:
                if isinstance(max_members_input, str):
                    max_members = (
                        int(max_members_input) if max_members_input.strip() else 100
                    )
                else:
                    max_members = int(max_members_input)
            except (ValueError, TypeError):
                max_members = 100

            max_members = max(1, min(max_members, 1000))

            # 방 이름 검증
            if not room_name:
                return Response(
                    {"success": False, "error": "방 이름을 입력해주세요."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if ChatRoom.objects.filter(name=room_name, is_active=True).exists():
                return Response(
                    {"success": False, "error": "이미 존재하는 방 이름입니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 방 생성 및 생성자 관리자 등록
            room = ChatRoom.objects.create(
                name=room_name,
                description=description or f"{room_name} 채팅방",
                max_members=max_members,
                created_by=request.user,
            )

            RoomMember.objects.create(
                room=room, user=request.user, is_admin=True, last_seen=timezone.now()
            )

            return Response(
                {
                    "success": True,
                    "room": {
                        "id": room.id,
                        "name": room.name,
                        "description": room.description,
                        "created_at": room.created_at.isoformat(),
                        "created_by": room.created_by.username,
                        "max_members": room.max_members,
                        "can_delete": True,
                    },
                    "message": f"{room_name} 채팅방이 성공적으로 생성되었습니다.",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            print(f"❌ 방 생성 오류: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RoomDeleteAPIView(APIView):
    """
    채팅방 삭제 API
    방 생성자만 삭제 가능, 실제 삭제가 아닌 비활성화 처리
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, room_id):
        try:
            try:
                room = ChatRoom.objects.get(id=room_id, is_active=True)
            except ChatRoom.DoesNotExist:
                return Response(
                    {"success": False, "error": "존재하지 않는 채팅방입니다."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # 생성자 권한 확인
            if room.created_by != request.user:
                return Response(
                    {"success": False, "error": "채팅방을 삭제할 권한이 없습니다."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # 방 비활성화 처리
            room_name = room.name
            room.is_active = False
            room.save()

            return Response(
                {"success": True, "message": f"{room_name} 채팅방이 삭제되었습니다."}
            )

        except Exception as e:
            print(f"❌ 방 삭제 오류: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RoomStatsAPIView(APIView):
    """
    서버 통계 API
    전체 방 수, 사용자 수, 온라인 사용자 수, 오늘 메시지 수 등 통계 반환
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            total_rooms = ChatRoom.objects.filter(is_active=True).count()
            total_users = User.objects.count()
            
            today = timezone.now().date()
            today_messages = ChatMessage.objects.filter(
                created_at__date=today, is_deleted=False
            ).count()

            try:
                online_users = UserProfile.objects.filter(is_online=True).count()
            except:
                online_users = 0

            return Response({
                "success": True,
                "stats": {
                    "total_rooms": total_rooms,
                    "total_users": total_users,
                    "online_users": online_users,
                    "today_messages": today_messages,
                    "server_status": "healthy",
                },
                "message": "통계 정보를 가져왔습니다.",
            })

        except Exception as e:
            print(f"❌ 통계 오류: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GetMessageAPIView(APIView):
    """
    채팅방 메시지 조회 API
    사용자가 입장한 시점 이후의 메시지만 조회
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, room_name):
        try:
            room = ChatRoom.objects.get(name=room_name, is_active=True)
            room_member = RoomMember.objects.get(room=room, user=request.user)

            # 입장 시점 이후 메시지만 조회
            messages = (
                ChatMessage.objects.filter(
                    room=room,
                    is_deleted=False,
                    created_at__gte=room_member.joined_at,
                )
                .select_related("user", "room")
                .order_by("created_at")
            )

            serializer = ChatMessageSerializer(messages, many=True)
            return Response(serializer.data)

        except ChatRoom.DoesNotExist:
            return Response(
                {"error": "존재하지 않는 채팅방입니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except RoomMember.DoesNotExist:
            return Response(
                {"error": "해당 방의 멤버가 아닙니다."},
                status=status.HTTP_403_FORBIDDEN,
            )


class JoinRoomAPIView(APIView):
    """
    채팅방 입장 API
    사용자를 방 멤버로 등록하고 실시간 접속 상태 True로 설정
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        try:
            room = ChatRoom.objects.get(name=room_name, is_active=True)
        except ChatRoom.DoesNotExist:
            return Response(
                {"detail": "존재하지 않는 채팅방입니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        current_members = RoomMember.objects.filter(room=room).count()
        member, created = RoomMember.objects.get_or_create(room=room, user=request.user)

        # 접속 상태 업데이트
        member.last_seen = timezone.now()
        member.is_currently_in_room = True
        member.save()

        online_members_count = RoomMember.objects.filter(room=room, is_currently_in_room=True).count()

        return Response({
            "success": True,
            "message": f"{request.user.username}님이 입장했습니다.",
            "room": {
                "id": room.id,
                "name": room.name,
                "description": room.description,
                "current_members": current_members + (1 if created else 0),
                "online_members": online_members_count, 
                "max_members": room.max_members,
            },
            "is_first": created,
        })


class LeaveRoomAPIView(APIView):
    """
    채팅방 퇴장 API
    사용자를 방 멤버에서 완전히 제거, 방이 비면 비활성화 처리
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        try:
            room = ChatRoom.objects.get(name=room_name, is_active=True)
        except ChatRoom.DoesNotExist:
            return Response(
                {"detail": "존재하지 않는 채팅방입니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 멤버 삭제
        deleted_count, _ = RoomMember.objects.filter(
            room=room, user=request.user
        ).delete()

        if deleted_count > 0:
            remaining_members = RoomMember.objects.filter(room=room)
            member_count = remaining_members.count()

            # 방이 비면 비활성화
            if member_count == 0:
                room.is_active = False
                room.save()
                return Response({
                    "success": True,
                    "message": f"{request.user.username}님이 퇴장했습니다. 방이 비활성화되었습니다.",
                    "room_deactivated": True,
                })
            else:
                # 첫 번째 남은 멤버를 관리자로 승격
                first_member = remaining_members.first()
                if first_member:
                    first_member.is_admin = True
                    first_member.save()

                return Response({
                    "success": True,
                    "message": f"{request.user.username}님이 퇴장했습니다.",
                    "remaining_members": member_count,
                    "room_deactivated": False,
                })
        else:
            return Response(
                {"success": False, "detail": "방에 참여하지 않은 상태입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RoomInfoAPIView(APIView):
    """
    채팅방 정보 조회 API
    특정 방의 상세 정보 및 현재 멤버 수, 온라인 멤버 수 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, room_name):
        try:
            room = ChatRoom.objects.get(name=room_name, is_active=True)
        except ChatRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "존재하지 않는 채팅방입니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        current_members = RoomMember.objects.filter(room=room).count()
        online_members = RoomMember.objects.filter(room=room, is_currently_in_room=True).count()

        return Response({
            "success": True,
            "room": {
                "id": room.id,
                "name": room.name,
                "description": room.description,
                "current_members": current_members,
                "online_members": online_members,
                "max_members": room.max_members,
                "created_by": room.created_by.username,
                "created_at": room.created_at,
            },
        })


class MarkAsReadAPIView(APIView):
    """
    메시지 읽음 처리 API
    사용자의 안 읽은 메시지들을 읽음 처리하고 WebSocket으로 실시간 업데이트 브로드캐스트
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        try:
            room = ChatRoom.objects.get(name=room_name)
            user = request.user
            member = RoomMember.objects.get(room=room, user=user)
            
            # 안 읽은 메시지 찾기
            last_read_time = member.last_read_message.created_at if member.last_read_message else timezone.make_aware(datetime.min)
            unread_messages = ChatMessage.objects.filter(
                room=room,
                created_at__gt=last_read_time,
                user__isnull=False  # 시스템 메시지 제외
            ).order_by('created_at')
            
            processed_count = 0
            updated_messages = []
            
            if unread_messages.exists():
                latest_message = unread_messages.latest('created_at')
                
                # 각 메시지 읽음 처리
                for message in unread_messages:
                    message.mark_as_read_by(user)
                    processed_count += 1
                    
                    message.refresh_from_db()
                    updated_messages.append({
                        'id': message.id,
                        'unread_count': message.unread_count,
                        'is_read_by_all': message.is_read_by_all
                    })
                
                # 멤버의 마지막 읽은 메시지 업데이트
                member.last_read_message = latest_message
                member.last_seen = timezone.now()
                member.save()
                
                # WebSocket으로 실시간 브로드캐스트
                if updated_messages:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"chat_{room_name}",
                        {
                            "type": "messages_read_count_update",
                            "updated_messages": updated_messages,
                            "reader_username": user.username
                        }
                    )
            
            return Response({
                'success': True,
                'message': f'{processed_count}개 메시지를 읽음 처리했습니다.',
                'processed_count': processed_count,
                'updated_messages': updated_messages
            })
            
        except (ChatRoom.DoesNotExist, RoomMember.DoesNotExist):
            return Response({
                'success': False,
                'error': '방을 찾을 수 없습니다.'
            }, status=404)
        except Exception as e:
            print(f"❌ 읽음 처리 오류: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)


class DisconnectRoomAPIView(APIView):
    """
    방 연결 해제 API
    사용자의 실시간 접속 상태만 False로 변경 (방 멤버십은 유지)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, room_name):
        try:
            room = ChatRoom.objects.get(name=room_name, is_active=True)
            member = RoomMember.objects.get(room=room, user=request.user)
            
            # 실시간 접속 상태만 변경
            member.is_currently_in_room = False
            member.last_seen = timezone.now()
            member.save()
            
            online_count = RoomMember.objects.filter(room=room, is_currently_in_room=True).count()
            
            return Response({
                "success": True,
                "message": f"{request.user.username}님의 연결이 해제되었습니다.",
                "online_members": online_count
            })
            
        except (ChatRoom.DoesNotExist, RoomMember.DoesNotExist):
            return Response({
                "success": False,
                "error": "방 또는 멤버를 찾을 수 없습니다."
            }, status=404)