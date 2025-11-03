from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="사용자")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="프로필 사진")
    bio = models.TextField(max_length=500, blank=True, verbose_name="자기소개")
    is_online = models.BooleanField(default=False, verbose_name="온라인 상태")
    last_activity = models.DateTimeField(default=timezone.now, verbose_name="마지막 활동")
    preferred_language = models.CharField(max_length=10, default="ko", verbose_name="선호 언어")
    class Meta:
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필들"

    def __str__(self):
        return f"{self.user.username}의 프로필"


class ChatRoom(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="방 이름")
    description = models.TextField(max_length=200, blank=True, verbose_name="방 설명")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_rooms", verbose_name="방 생성자")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")
    is_active = models.BooleanField(default=True, verbose_name="활성 상태")
    max_members = models.PositiveIntegerField(default=100, verbose_name="최대 인원")
    is_private = models.BooleanField(default=False, verbose_name="비공개 방")
    password = models.CharField(max_length=20, blank=True, verbose_name="방 비밀번호")

    class Meta:
        verbose_name = "채팅방"
        verbose_name_plural = "채팅방들"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def total_messages(self):
        """총 메시지 수"""
        return self.messages.count()


class RoomMember(models.Model):
    """채팅방 멤버 관리"""

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="members", verbose_name="채팅방")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="joined_rooms", verbose_name="사용자")
    is_admin = models.BooleanField(default=False, verbose_name="관리자 권한")
    nickname = models.CharField(max_length=30, blank=True, verbose_name="방 내 닉네임")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="입장일시")
    last_seen = models.DateTimeField(default=timezone.now, verbose_name="방 마지막 접속")
    is_currently_in_room = models.BooleanField(default=False, verbose_name="현재 방에 접속 중")
    last_read_message = models.ForeignKey("ChatMessage", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="마지막으로 읽은 메시지")
    class Meta:
        verbose_name = "방 멤버"
        verbose_name_plural = "방 멤버들"
        unique_together = ["room", "user"]  # 한 방에 같은 유저는 한 번만
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.user.username} in {self.room.name}"


class ChatMessage(models.Model):
    """채팅 메시지 모델"""

    MESSAGE_TYPES = [
        ("text", "일반 텍스트"),
        ("image", "이미지"),
        ("file", "파일"),
        ("system", "시스템 메시지"),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages", verbose_name="채팅방")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_messages", verbose_name="작성자")
    content = models.TextField(verbose_name="메시지 내용")
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default="text", verbose_name="메시지 타입")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일시")
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name="수정일시")
    is_deleted = models.BooleanField(default=False, verbose_name="삭제 여부")
    file_url = models.URLField(blank=True, verbose_name="파일 URL")
    reply_to = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies", verbose_name="답장 대상")
    unread_count = models.PositiveIntegerField(default=0, verbose_name="안 읽은 수")
    total_members_at_time = models.PositiveIntegerField(default=0, verbose_name="메시지 전송 당시 총 멤버 수")
    class Meta:
        verbose_name = "채팅 메시지"
        verbose_name_plural = "채팅 메시지들"
        ordering = ["created_at"]

    def __str__(self):
        username = self.user.username if self.user else "시스템"
        return f"{username}: {self.content[:50]}..."

    @property
    def author_name(self):
        """작성자 이름 (닉네임 우선)"""
        if not self.user:
            return "시스템"

        try:
            member = RoomMember.objects.get(room=self.room, user=self.user)
            return member.nickname if member.nickname else self.user.username
        except RoomMember.DoesNotExist:
            return self.user.username

    @property
    def is_read_by_all(self):
        """메시지 전송 당시 방에 있던 모든 멤버가 읽었는지 여부"""
        return self.unread_count == 0

    def mark_as_read_by(self, user):
        """특정 사용자가 읽음 처리"""
        if self.unread_count > 0:
            # 이 사용자가 메시지 생성 당시 방에 있었는지 확인
            try:
                member = RoomMember.objects.get(
                    room=self.room, 
                    user=user,
                    joined_at__lte=self.created_at
                )
                # 아직 이 메시지를 읽지 않았다면 읽음 처리
                if not member.last_read_message or member.last_read_message.created_at < self.created_at:
                    member.last_read_message = self
                    member.save()
                    self.unread_count = max(0, self.unread_count - 1)
                    self.save(update_fields=['unread_count'])
            except RoomMember.DoesNotExist:
                pass
    
    def save(self, *args, **kwargs):
        """메시지 저장 시 초기 읽음 수 설정"""
        if self.pk is None:  # 새로 생성되는 메시지
            # 메시지 생성 당시 방의 총 멤버 수
            current_members = RoomMember.objects.filter(
                room=self.room,
                joined_at__lte=timezone.now()
            ).count()
            
            self.total_members_at_time = current_members
            # 작성자 제외한 모든 멤버가 안 읽은 상태로 시작
            self.unread_count = max(0, current_members - 1) if self.user else current_members
            
        super().save(*args, **kwargs)
        
        # 저장 후 작성자는 자동으로 읽음 처리
        if self.user and self.pk:
            try:
                member = RoomMember.objects.get(room=self.room, user=self.user)
                member.last_read_message = self
                member.save(update_fields=['last_read_message'])
            except RoomMember.DoesNotExist:
                pass

class MessageReaction(models.Model):
    """메세지 이모지 반응 모델"""
    REACTION_CHOICES = [
        ("like", "like"),
        ("good", "good"),
        ("check", "check"),
    ]
    user = models.ForeignKey( User, on_delete=models.CASCADE, related_name="user_reactions", verbose_name="사용자")
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="message_reactions", verbose_name="메시지")
    reaction_type = models.CharField(max_length=50, choices=REACTION_CHOICES, verbose_name="반응유형")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="반응일시")

    class Meta:
        verbose_name = "메시지 반응"
        verbose_name_plural = "메시지 반응들"
        unique_together = ["user", "message", "reaction_type"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['message', 'reaction_type']),
        ]

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction_type} to message {self.message.id}"