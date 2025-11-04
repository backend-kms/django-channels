from django.utils import timezone
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatMessage, ChatRoom, RoomMember


class ChatConsumer(AsyncWebsocketConsumer):
    """
    실시간 채팅 WebSocket Consumer
    메시지 송수신, 입퇴장 알림, 읽음 처리를 담당
    """
    
    async def connect(self):
        """WebSocket 연결 설정"""
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        self.username = None

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        if hasattr(self, 'username') and self.username:
            await self.update_online_status(False)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신 처리"""
        try:
            data = json.loads(text_data)
            username = data.get("username")
            message_type = data.get("type")
            
            if message_type == 'user_join':
                await self.handle_user_join(username)
            elif message_type == 'user_leave':
                await self.handle_user_leave(username)
            elif message_type == 'text':
                await self.handle_text_message(username, data.get("message", ""))
            elif message_type == 'mark_read':
                await self.handle_mark_read(username, data.get('message_id'))
                
        except json.JSONDecodeError:
            print("❌ JSON 파싱 오류")
        except Exception as e:
            print(f"❌ 메시지 처리 오류: {e}")

    # 메시지 타입별 핸들러
    async def handle_user_join(self, username):
        """사용자 입장 처리"""
        self.username = username
        await self.update_online_status(True)
        
        # 기존 메시지들의 읽음 수 업데이트
        updated_messages = await self.update_existing_messages_read_count()
        
        # 입장 메시지 전송
        message = f"{username}님이 입장했습니다."
        await self.save_message(username, message, "system")
        await self.channel_layer.group_send(
            self.room_group_name, 
            {
                "type": "system_message", 
                "message": message, 
                "username": username
            }
        )
        
        # 기존 메시지 읽음 수 업데이트 알림
        if updated_messages:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "messages_read_count_update",
                    "updated_messages": updated_messages
                }
            )

    async def handle_user_leave(self, username):
        """사용자 퇴장 처리"""
        message = f"{username}님이 퇴장했습니다."
        await self.save_message(username, message, "system")
        await self.channel_layer.group_send(
            self.room_group_name, 
            {
                "type": "system_message", 
                "message": message, 
                "username": username
            }
        )

    async def handle_text_message(self, username, message):
        """텍스트 메시지 처리"""
        self.username = username
        message_data = await self.save_message_with_read_info(username, message, "text")
        
        if message_data:
            await self.channel_layer.group_send(
                self.room_group_name, 
                {
                    "type": "chat_message", 
                    "message": message, 
                    "username": username,
                    "message_id": message_data['id'],
                    "unread_count": message_data['unread_count'],
                    "is_read_by_all": message_data['is_read_by_all'],
                    "user_id": message_data['user_id']
                }
            )

    async def handle_mark_read(self, username, message_id):
        """읽음 처리"""
        if message_id:
            await self.mark_message_read(username, message_id)

    # WebSocket 이벤트 핸들러
    async def chat_message(self, event):
        """채팅 메시지 전송"""
        await self.send(text_data=json.dumps({
            "message": event["message"], 
            "username": event["username"],
            "type": "chat",
            "message_id": event.get("message_id"),
            "unread_count": event.get("unread_count", 0),
            "is_read_by_all": event.get("is_read_by_all", True),
            "user_id": event.get("user_id"),
            "timestamp": timezone.now().isoformat()
        }))
    
    async def system_message(self, event):
        """시스템 메시지 전송"""
        await self.send(text_data=json.dumps({
            "message": event["message"], 
            "username": event["username"],
            "type": "system"
        }))

    async def messages_read_count_update(self, event):
        """메시지 읽음 수 업데이트 전송"""
        await self.send(text_data=json.dumps({
            "type": "messages_read_count_update",
            "updated_messages": event["updated_messages"],
            "reader_username": event.get("reader_username")
        }))
    
    async def reaction_update(self, event):
        await self.send(text_data=json.dumps({
        'type': 'reaction_update',
        'message_id': event['message_id'],
        'action': event['action'],
        'reaction_type': event['reaction_type'],
        'reaction_counts': event['reaction_counts'],
        'user': event['user']
    }))

    # 데이터베이스 작업
    @database_sync_to_async
    def save_message(self, username, message, message_type):
        """기본 메시지 저장"""
        try:
            user = User.objects.get(username=username)
            room = ChatRoom.objects.get(name=self.room_name)
            return ChatMessage.objects.create(
                room=room,
                user=user,
                content=message,
                message_type=message_type
            )
        except (User.DoesNotExist, ChatRoom.DoesNotExist):
            return None
    
    @database_sync_to_async
    def save_message_with_read_info(self, username, message, message_type):
        """메시지 저장 + 실시간 접속자 읽음 처리"""
        try:
            user = User.objects.get(username=username)
            room = ChatRoom.objects.get(name=self.room_name)
            
            # 메시지 생성
            chat_message = ChatMessage.objects.create(
                room=room,
                user=user,
                content=message,
                message_type=message_type
            )

            # 현재 온라인인 모든 멤버를 자동 읽음 처리
            online_members = RoomMember.objects.filter(
                room=room, 
                is_currently_in_room=True
            )

            for member in online_members:
                chat_message.mark_as_read_by(member.user)
        
            # 업데이트된 정보 반환
            chat_message.refresh_from_db()
            return {
                'id': chat_message.id,
                'unread_count': chat_message.unread_count,
                'is_read_by_all': chat_message.is_read_by_all,
                'user_id': user.id
            }
        except Exception as e:
            print(f"❌ 메시지 저장 오류: {e}")
            return None

    @database_sync_to_async
    def update_existing_messages_read_count(self):
        """기존 메시지들의 읽음 수 재계산 (사용자 입장 시)"""
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            
            # 최근 메시지들만 처리 (성능 최적화)
            recent_messages = ChatMessage.objects.filter(
                room=room,
                is_deleted=False,
                message_type='text'
            ).order_by('-created_at')[:50]
            
            # 현재 온라인 멤버들
            online_members = RoomMember.objects.filter(
                room=room, 
                is_currently_in_room=True
            )
            
            updated_messages = []
            
            for message in recent_messages:
                # 온라인 멤버들을 읽음 처리
                for member in online_members:
                    message.mark_as_read_by(member.user)
                
                # 업데이트된 정보 수집
                message.refresh_from_db()
                updated_messages.append({
                    'id': message.id,
                    'unread_count': message.unread_count,
                    'is_read_by_all': message.is_read_by_all
                })
            
            return updated_messages
            
        except ChatRoom.DoesNotExist:
            return []

    @database_sync_to_async
    def mark_message_read(self, username, message_id):
        """특정 메시지 읽음 처리"""
        try:
            user = User.objects.get(username=username)
            message = ChatMessage.objects.get(id=message_id)
            message.mark_as_read_by(user)
        except (User.DoesNotExist, ChatMessage.DoesNotExist):
            pass

    @database_sync_to_async
    def update_online_status(self, is_online):
        """온라인 상태 업데이트"""
        if not hasattr(self, 'username') or not self.username:
            return
        
        try:
            user = User.objects.get(username=self.username)
            room = ChatRoom.objects.get(name=self.room_name)
            member, created = RoomMember.objects.get_or_create(room=room, user=user)
            member.is_currently_in_room = is_online
            member.last_seen = timezone.now()
            member.save()
        except (User.DoesNotExist, ChatRoom.DoesNotExist):
            pass