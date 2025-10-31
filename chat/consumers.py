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
            await self.save_message(username, message, "text")  # message_type 추가
            await self.channel_layer.group_send(
                self.room_group_name, 
                {
                    "type": "chat_message", 
                    "message": message, 
                    "username": username
                }
            )

    # 일반 채팅 메시지 핸들러
    async def chat_message(self, event):
        message = event["message"]
        username = event["username"]

        await self.send(text_data=json.dumps({
            "message": message, 
            "username": username,
            "type": "chat"
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