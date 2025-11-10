from datetime import datetime
import mimetypes
import os
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
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
    PushSubscriptionSerializer,
)
from .models import ChatRoom, ChatMessage, MessageReaction, PushSubscription, RoomMember, UserProfile
from django.utils import timezone
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import MultiPartParser, FormParser


# 테스트용 템플릿 뷰
def index(request):
    """채팅 메인 페이지"""
    return render(request, "chat/index.html")

def room(request, room_name):
    """채팅방 페이지"""
    return render(request, "chat/room.html", {"room_name": room_name})


# 인증 관련 API
class LoginAPIView(APIView):
    """
    JWT 기반 로그인 API
    사용자 인증 후 access_token과 refresh_token 반환
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
                    {"success": False, "detail": "아이디 또는 비밀번호가 틀렸습니다."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except Exception as e:
            return Response(
                {"success": False, "detail": str(e)},
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
            return Response(
                {"success": False, "detail": str(e)},
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
            return Response(
                {"success": False, "detail": str(e)},
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
            # 본인이 속한 방 ID 목록 조회
            rooms_in_me = (
                RoomMember.objects.filter(
                    user=request.user, room__is_active=True
                ).values_list("room_id", flat=True)
                if request.user.is_authenticated
                else []
            )
            
            # 본인이 속하지 않은 활성 채팅방 조회 (최대 20개)
            rooms = (
                ChatRoom.objects.filter(is_active=True)
                .exclude(id__in=rooms_in_me)
                .select_related("created_by")[:20]
            )

            rooms_data = []
            for room in rooms:
                # 삭제 권한 확인 (방 생성자만 가능)
                can_delete = (
                    request.user.is_authenticated and 
                    room.created_by and 
                    room.created_by == request.user
                )

                rooms_data.append({
                    "id": room.id,
                    "name": room.name,
                    "description": room.description,
                    "created_at": room.created_at.isoformat(),
                    "created_by": room.created_by.username if room.created_by else "알 수 없음",
                    "max_members": room.max_members,
                    "member_count": RoomMember.objects.filter(room=room).count(),
                    "can_delete": can_delete,
                })

            return Response({"results": rooms_data})

        except Exception as e:
            return Response(
                {"success": False, "detail": str(e)},
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
            # 사용자가 속한 모든 활성 방 조회 (최근 접속순)
            my_memberships = (
                RoomMember.objects.filter(user=request.user, room__is_active=True)
                .select_related("room", "room__created_by")
                .order_by("-last_seen")
            )

            rooms_data = []
            for membership in my_memberships:
                room = membership.room
                current_member_count = RoomMember.objects.filter(room=room).count()

                # 안읽은 메시지 수 계산
                last_read_time = (
                    membership.last_read_message.created_at 
                    if membership.last_read_message 
                    else timezone.make_aware(datetime.min)
                )
                unread_count = ChatMessage.objects.filter(
                    room=room,
                    created_at__gt=last_read_time,
                    user__isnull=False,  # 시스템 메시지 제외
                    is_deleted=False
                ).count()

                # 마지막 메시지 정보 조회
                last_message = ChatMessage.objects.filter(
                    room=room,
                    is_deleted=False,
                    user__isnull=False
                ).order_by('-created_at').first()

                last_message_content = last_message.content if last_message else None
                last_message_time = last_message.created_at.isoformat() if last_message else None

                rooms_data.append({
                    "id": room.id,
                    "name": room.name,
                    "description": room.description,
                    "created_at": room.created_at.isoformat(),
                    "created_by": room.created_by.username if room.created_by else "알 수 없음",
                    "max_members": room.max_members,
                    "member_count": current_member_count,
                    "is_admin": membership.is_admin,
                    "last_seen": membership.last_seen.isoformat() if membership.last_seen else None,
                    "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
                    "unread_count": unread_count,
                    "last_message": last_message_content,
                    "last_message_time": last_message_time,
                })

            return Response(rooms_data)

        except Exception as e:
            return Response(
                {"success": False, "detail": str(e)},
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

            # 최대 인원수 정수 변환 및 범위 제한 (1-1000)
            try:
                if isinstance(max_members_input, str):
                    max_members = int(max_members_input) if max_members_input.strip() else 100
                else:
                    max_members = int(max_members_input)
            except (ValueError, TypeError):
                max_members = 100

            max_members = max(1, min(max_members, 1000))

            # 방 이름 검증
            if not room_name:
                return Response(
                    {"success": False, "detail": "방 이름을 입력해주세요."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 중복 방 이름 확인
            if ChatRoom.objects.filter(name=room_name, is_active=True).exists():
                return Response(
                    {"success": False, "detail": "이미 존재하는 방 이름입니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 방 생성
            room = ChatRoom.objects.create(
                name=room_name,
                description=description or f"{room_name} 채팅방",
                max_members=max_members,
                created_by=request.user,
            )

            # 생성자를 관리자로 자동 등록
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
            return Response(
                {"success": False, "detail": str(e)},
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
                    {"success": False, "detail": "존재하지 않는 채팅방입니다."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # 생성자 권한 확인
            if room.created_by != request.user:
                return Response(
                    {"success": False, "detail": "채팅방을 삭제할 권한이 없습니다."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # 방 비활성화 처리 (실제 삭제 X)
            room_name = room.name
            room.is_active = False
            room.save()

            return Response(
                {"success": True, "message": f"{room_name} 채팅방이 삭제되었습니다."}
            )

        except Exception as e:
            return Response(
                {"success": False, "detail": str(e)},
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
            # 서버 통계 데이터 수집
            total_rooms = ChatRoom.objects.filter(is_active=True).count()
            total_users = User.objects.count()
            
            today = timezone.now().date()
            today_messages = ChatMessage.objects.filter(
                created_at__date=today, is_deleted=False
            ).count()

            # 온라인 사용자 수 (안전하게 처리)
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
            return Response(
                {"success": False, "detail": str(e)},
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

            # 사용자 입장 시점 이후 메시지만 조회
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
                {"detail": "존재하지 않는 채팅방입니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except RoomMember.DoesNotExist:
            return Response(
                {"detail": "해당 방의 멤버가 아닙니다."},
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

        # 실시간 접속 상태 업데이트
        member.last_seen = timezone.now()
        member.is_currently_in_room = True
        member.save()

        online_members_count = RoomMember.objects.filter(room=room, is_currently_in_room=True).count()

        # 글로벌 WebSocket으로 안읽은 수 업데이트 브로드캐스트
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            # 현재 사용자의 안읽은 메시지 수 계산
            last_read_time = (
                member.last_read_message.created_at 
                if member.last_read_message 
                else timezone.make_aware(datetime.min)
            )
            
            unread_count = ChatMessage.objects.filter(
                room=room,
                created_at__gt=last_read_time,
                user__isnull=False,
                is_deleted=False
            ).count()
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{request.user.id}_global",
                {
                    "type": "unread_count_update",
                    "room_name": room_name,
                    "unread_count": unread_count
                }
            )
        except Exception as e:
            print(f"입장 시 글로벌 WebSocket 브로드캐스트 오류: {e}")

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

        try:
            member = RoomMember.objects.get(room=room, user=request.user)
            
            # 나가기 전 안 읽은 메시지들을 모두 읽음 처리
            last_read_time = (
                member.last_read_message.created_at 
                if member.last_read_message 
                else timezone.make_aware(datetime.min)
            )
            unread_messages = ChatMessage.objects.filter(
                room=room,
                created_at__gt=last_read_time,
                user__isnull=False,  # 시스템 메시지 제외
                is_deleted=False
            ).order_by('created_at')
            
            processed_count = 0
            updated_messages = []
            
            if unread_messages.exists():
                latest_message = unread_messages.latest('created_at')
                
                # 각 메시지 읽음 처리
                for message in unread_messages:
                    if message.mark_as_read_by(request.user):
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
                
                # WebSocket으로 실시간 브로드캐스트 (나가기 전에)
                if updated_messages:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"chat_{room_name}",
                        {
                            "type": "messages_read_count_update",
                            "updated_messages": updated_messages,
                            "reader_username": request.user.username
                        }
                    )

        except RoomMember.DoesNotExist:
            return Response(
                {"success": False, "detail": "방에 참여하지 않은 상태입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 멤버 완전 삭제
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
                    "messages_read": processed_count
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
                    "messages_read": processed_count
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
                {"success": False, "detail": "존재하지 않는 채팅방입니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 방 통계 정보 계산
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
            last_read_time = (
                member.last_read_message.created_at 
                if member.last_read_message 
                else timezone.make_aware(datetime.min)
            )
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
                    
                    # 글로벌 WebSocket으로도 안읽은 수 업데이트 브로드캐스트
                    final_unread_count = ChatMessage.objects.filter(
                        room=room,
                        created_at__gt=latest_message.created_at,
                        user__isnull=False,
                        is_deleted=False
                    ).count()
                    
                    async_to_sync(channel_layer.group_send)(
                        f"user_{user.id}_global",
                        {
                            "type": "unread_count_update",
                            "room_name": room_name,
                            "unread_count": final_unread_count
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
                'detail': '방을 찾을 수 없습니다.'
            }, status=404)
        except Exception as e:
            return Response({
                'success': False,
                'detail': str(e)
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
                "detail": "방 또는 멤버를 찾을 수 없습니다."
            }, status=404)


# 메시지 반응 관련 API
class CreateReactionAPIView(APIView):
    """
    메시지 리액션 추가/수정/제거 API
    사용자가 특정 메시지에 리액션을 추가하거나 제거
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        try:
            reaction_type = request.data.get("reaction_type", "").strip()
            
            # 유효한 반응 타입인지 확인
            if reaction_type not in dict(MessageReaction.REACTION_CHOICES):
                return JsonResponse({'detail': '잘못된 반응 타입입니다.'}, status=400)

            message = get_object_or_404(ChatMessage, id=message_id)

            # 기존 반응 확인
            existing_reaction = MessageReaction.objects.filter(
                message=message, user=request.user
            ).first()

            if existing_reaction:
                if existing_reaction.reaction_type == reaction_type:
                    # 동일한 리액션이면 제거
                    existing_reaction.delete()
                    action = "removed"
                else:
                    # 다른 리액션이면 업데이트
                    existing_reaction.reaction_type = reaction_type
                    existing_reaction.save()
                    action = "updated"
            else:
                # 새로운 리액션 추가
                MessageReaction.objects.create(
                    message=message,
                    user=request.user,
                    reaction_type=reaction_type
                )
                action = "added"
            
            # 모든 반응 타입별 개수 계산
            reaction_counts = {}
            for choice_key, choice_value in MessageReaction.REACTION_CHOICES:
                count = MessageReaction.objects.filter(
                    message=message,
                    reaction_type=choice_key
                ).count()
                reaction_counts[choice_key] = count
            
            # WebSocket으로 실시간 업데이트 브로드캐스트
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                room_name = message.room.name
                
                async_to_sync(channel_layer.group_send)(
                    f"chat_{room_name}",
                    {
                        "type": "reaction_update",
                        "message_id": message_id,
                        "action": action,
                        "reaction_type": reaction_type,
                        "reaction_counts": reaction_counts,
                        "user": request.user.username
                    }
                )
            except Exception as e:
                print(f"WebSocket 브로드캐스트 오류: {e}")
                
            return JsonResponse({
                'success': True,
                'action': action,
                'reaction_type': reaction_type,
                'reaction_counts': reaction_counts
            })

        except Exception as e:
            return JsonResponse({'detail': str(e)}, status=500)


class ReactionAPIView(APIView):
    """
    메시지 리액션 조회 API
    특정 메시지에 대한 모든 리액션과 현재 사용자의 반응 상태 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, message_id):
        try:
            message = get_object_or_404(ChatMessage, id=message_id)
            
            reaction_counts = {}
            user_reaction = None

            # 모든 반응 타입별 개수 및 사용자 반응 확인
            for choice_key, choice_value in MessageReaction.REACTION_CHOICES:
                reactions = MessageReaction.objects.filter(
                    message=message,
                    reaction_type=choice_key
                ).select_related('user')
                
                count = reactions.count()
                reaction_counts[choice_key] = count
                
                # 현재 사용자가 이 반응을 했는지 확인
                user_reacted = reactions.filter(user=request.user).exists()
                if user_reacted:
                    user_reaction = choice_key
            
            return JsonResponse({
                'reaction_counts': reaction_counts,
                'user_reaction': user_reaction
            })

        except Exception as e:
            return JsonResponse({'detail': str(e)}, status=500)


# 파일 업로드 API
class FileUploadAPIView(APIView):
    """
    파일 업로드 API
    채팅 메시지에 첨부할 파일 업로드 처리
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, room_name):
        try:
            room = ChatRoom.objects.get(name=room_name, is_active=True)
            user = request.user

            # 방 멤버 권한 확인
            if not RoomMember.objects.filter(room=room, user=user).exists():
                return Response(
                    {'success': False, 'detail': '해당 방의 멤버가 아닙니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response(
                    {'success': False, 'detail': '업로드할 파일이 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 파일 타입 확인
            content_type, _ = mimetypes.guess_type(uploaded_file.name)
            is_image = content_type and content_type.startswith('image/')
            message_type = 'image' if is_image else 'file'

            # 이미지 확장자 검증
            allowed_image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()

            if message_type == 'image' and file_extension not in allowed_image_extensions:
                message_type = 'file'
            
            # 채팅 메시지 생성
            chat_message = ChatMessage.objects.create(
                room=room,
                user=user,
                content='',
                message_type=message_type,
                file=uploaded_file,
                file_name=uploaded_file.name,
                file_size=uploaded_file.size,
            )

            # WebSocket으로 실시간 브로드캐스트
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{room_name}",
                {
                    'type': 'file_message',
                    'message_id': chat_message.id,
                    'username': user.username,
                    'user_id': user.id,
                    'file_name': chat_message.file_name,
                    'file_size': chat_message.file_size,
                    'file_size_human': chat_message.file_size_human,
                    'file_url': chat_message.file.url if chat_message.file else None,
                    'message_type': message_type,
                    'timestamp': chat_message.created_at.isoformat(),
                    'content': None,
                    'is_image': message_type == 'image'
                }
            )

            members = RoomMember.objects.filter(room=room).select_related('user', 'last_read_message')
            for member in members:
                last_read_time = (
                    member.last_read_message.created_at 
                    if member.last_read_message 
                    else timezone.make_aware(datetime.min)
                )
                unread_count = ChatMessage.objects.filter(
                    room=room,
                    created_at__gt=last_read_time,
                    user__isnull=False,
                    is_deleted=False,
                ).count()
                async_to_sync(channel_layer.group_send)(
                    f"user_{member.user.id}_global",
                    {
                        "type": "unread_count_update",
                        "room_name": room_name,
                        "unread_count": unread_count
                    }
                )
            
            return Response({
                'success': True,
                'message': f'{"이미지" if message_type == "image" else "파일"}가 업로드되었습니다.',
                'file': {
                    'id': chat_message.id,
                    'name': chat_message.file_name,
                    'size': chat_message.file_size,
                    'size_human': chat_message.file_size_human,
                    'url': chat_message.file.url if chat_message.file else None,
                    'type': message_type,
                    'is_image': message_type == 'image'
                }
            })

        except Exception as e:
            return Response(
                {'success': False, 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

def notification_test(request):
    """알림 테스트 페이지 (오류 수정)"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>알림 테스트</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            button { padding: 10px 20px; margin: 10px; font-size: 16px; }
            #status { margin-top: 20px; padding: 10px; border: 1px solid #ccc; }
            .success { background-color: #d4edda; }
            .error { background-color: #f8d7da; }
        </style>
    </head>
    <body>
        <h1>푸시 알림 테스트 (오류 수정)</h1>
        <button id="testButton">알림 테스트하기</button>
        <button id="requestPermission">알림 권한 요청</button>
        <button id="checkPermission">현재 권한 상태 확인</button>
        <button id="forceNotification">강제 알림 (간단 버전)</button>
        
        <div id="status"></div>
        
        <script>
            const statusDiv = document.getElementById('status');
            
            // 페이지 로드 시 전체 상태 확인
            window.onload = function() {
                checkAllStatus();
            };
            
            function checkAllStatus() {
                let status = '';
                status += '<h3>현재 상태</h3>';
                status += '<p>알림 권한: <strong>' + Notification.permission + '</strong></p>';
                status += '<p>브라우저 지원: <strong>' + (('Notification' in window) ? '지원함' : '지원안함') + '</strong></p>';
                status += '<p>현재 URL: <strong>' + window.location.href + '</strong></p>';
                status += '<p>HTTPS 여부: <strong>' + (window.location.protocol === 'https:' ? 'HTTPS' : 'HTTP') + '</strong></p>';
                statusDiv.innerHTML = status;
            }
            
            // 권한 상태 확인
            document.getElementById('checkPermission').onclick = checkAllStatus;
            
            // 권한 요청
            document.getElementById('requestPermission').onclick = async function() {
                try {
                    console.log('권한 요청 시작...');
                    const permission = await Notification.requestPermission();
                    console.log('권한 결과:', permission);
                    
                    const className = permission === 'granted' ? 'success' : 'error';
                    statusDiv.innerHTML = '<div class="' + className + '">권한 결과: <strong>' + permission + '</strong></div>';
                    
                    if (permission === 'granted') {
                        alert('알림 권한이 허용되었습니다!');
                    } else if (permission === 'denied') {
                        alert('알림 권한이 거부되었습니다. 브라우저 설정에서 수동으로 허용해주세요.');
                    } else {
                        alert('알림 권한 요청이 무시되었습니다.');
                    }
                    
                    setTimeout(checkAllStatus, 1000);
                } catch (error) {
                    console.error('권한 요청 에러:', error);
                    statusDiv.innerHTML = '<div class="error">에러: ' + error.message + '</div>';
                }
            };
            
            // 기본 알림 테스트
            document.getElementById('testButton').onclick = function() {
                console.log('=== 알림 테스트 시작 ===');
                console.log('권한 상태:', Notification.permission);
                
                if (Notification.permission !== 'granted') {
                    statusDiv.innerHTML = '<div class="error">알림 권한이 허용되지 않았습니다. 현재 상태: ' + Notification.permission + '</div>';
                    return;
                }
                
                try {
                    console.log('알림 생성 중...');
                    
                    const notification = new Notification('🔔 테스트 알림', {
                        body: '이 알림이 보이면 성공입니다! 클릭해보세요.',
                        tag: 'test-' + Date.now(),
                        requireInteraction: false,
                        silent: false
                    });
                    
                    console.log('알림 객체 생성됨:', notification);
                    
                    // 이벤트 리스너 등록
                    notification.onshow = function() {
                        console.log('✅ 알림이 화면에 표시됨!');
                        statusDiv.innerHTML = '<div class="success">✅ 알림이 성공적으로 표시되었습니다!</div>';
                    };
                    
                    notification.onerror = function(error) {
                        console.error('❌ 알림 표시 오류:', error);
                        statusDiv.innerHTML = '<div class="error">❌ 알림 표시 중 오류 발생</div>';
                    };
                    
                    notification.onclick = function() {
                        console.log('알림 클릭됨');
                        window.focus();
                        notification.close();
                    };
                    
                    notification.onclose = function() {
                        console.log('알림이 닫힘');
                    };
                    
                    // 5초 후 상태 확인
                    setTimeout(function() {
                        if (!statusDiv.innerHTML.includes('성공적으로 표시')) {
                            statusDiv.innerHTML += '<div class="error">⚠️ 5초가 지났지만 onshow 이벤트가 발생하지 않았습니다.</div>';
                        }
                    }, 5000);
                    
                } catch (error) {
                    console.error('알림 생성 실패:', error);
                    statusDiv.innerHTML = '<div class="error">알림 생성 실패: ' + error.message + '</div>';
                }
            };
            
            // 강제 알림 (가장 간단한 버전)
            document.getElementById('forceNotification').onclick = function() {
                if (Notification.permission !== 'granted') {
                    alert('먼저 알림 권한을 허용해주세요!');
                    return;
                }
                
                console.log('강제 알림 시도...');
                
                try {
                    // 최소한의 옵션으로 알림 생성
                    const simpleNotification = new Notification('간단한 알림');
                    
                    simpleNotification.onshow = function() {
                        console.log('간단한 알림 표시됨');
                        statusDiv.innerHTML = '<div class="success">간단한 알림이 표시되었습니다!</div>';
                    };
                    
                    simpleNotification.onerror = function(error) {
                        console.log('간단한 알림도 실패:', error);
                        statusDiv.innerHTML = '<div class="error">간단한 알림도 실패했습니다.</div>';
                    };
                    
                    console.log('간단한 알림 객체:', simpleNotification);
                    
                } catch (error) {
                    console.error('간단한 알림 생성 오류:', error);
                    statusDiv.innerHTML = '<div class="error">간단한 알림 생성 실패: ' + error.message + '</div>';
                }
            };
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_content)


class SaveSubscriptionView(APIView):
    def post(self, request):
        data = request.data
        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')
        user = request.user if request.user.is_authenticated else None

        if not endpoint or not p256dh or not auth:
            return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

        sub, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={'user': user, 'p256dh': p256dh, 'auth': auth}
        )
        serializer = PushSubscriptionSerializer(sub)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)