from django.utils import timezone
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import User, ChatMessage, ChatRoom

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        self.username = None

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        username = text_data_json.get("username")
        message_type = text_data_json.get("type")
        
        if message_type == 'user_join':
            self.username = username
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
        elif message_type == 'user_leave':
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
        elif message_type == 'text':
            message = text_data_json.get("message", "")
            self.username = username
            # 🔑 메시지 저장하고 읽음 정보도 함께 가져오기
            message_data = await self.save_message_with_read_info(username, message, "text")
            
            await self.channel_layer.group_send(
                self.room_group_name, 
                {
                    "type": "chat_message", 
                    "message": message, 
                    "username": username,
                    "message_id": message_data['id'] if message_data else None,
                    "unread_count": message_data['unread_count'] if message_data else 0,
                    "is_read_by_all": message_data['is_read_by_all'] if message_data else True,
                    "user_id": message_data['user_id'] if message_data else None
                }
            )

    # 일반 채팅 메시지 핸들러
    async def chat_message(self, event):
        message = event["message"]
        username = event["username"]
        message_id = event.get("message_id")
        unread_count = event.get("unread_count", 0)
        is_read_by_all = event.get("is_read_by_all", True)
        user_id = event.get("user_id")

        await self.send(text_data=json.dumps({
            "message": message, 
            "username": username,
            "type": "chat",
            "message_id": message_id,
            "unread_count": unread_count,
            "is_read_by_all": is_read_by_all,
            "user_id": user_id,
            "timestamp": timezone.now().isoformat()
        }))
    
    # 시스템 메시지 핸들러 (입장/퇴장용)
    async def system_message(self, event):
        message = event["message"]
        username = event["username"]

        await self.send(text_data=json.dumps({
            "message": message, 
            "username": username,
            "type": "system"
        }))
    
    @database_sync_to_async
    def save_message(self, username, message, message_type):
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
        try:
            user = User.objects.get(username=username)
            room = ChatRoom.objects.get(name=self.room_name)
            chat_message = ChatMessage.objects.create(
                room=room,
                user=user,
                content=message,
                message_type=message_type
            )
            
            # 🔑 save() 메서드에서 자동으로 unread_count 계산됨
            return {
                'id': chat_message.id,
                'unread_count': chat_message.unread_count,  # 이미 계산된 값
                'is_read_by_all': chat_message.is_read_by_all,
                'user_id': user.id
            }
        except (User.DoesNotExist, ChatRoom.DoesNotExist):
            return None