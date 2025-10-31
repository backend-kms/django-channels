from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class UserProfile(models.Model):
    """사용자 프로필 확장"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name="profile",
        verbose_name="사용자"
    )
    avatar = models.ImageField(
        upload_to='avatars/', 
        blank=True, 
        null=True,
        verbose_name="프로필 사진"
    )
    bio = models.TextField(max_length=500, blank=True, verbose_name="자기소개")
    is_online = models.BooleanField(default=False, verbose_name="온라인 상태")
    last_activity = models.DateTimeField(default=timezone.now, verbose_name="마지막 활동")
    preferred_language = models.CharField(
        max_length=10, 
        default='ko',
        verbose_name="선호 언어"
    )
    
    class Meta:
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필들"
    
    def __str__(self):
        return f"{self.user.username}의 프로필"

class ChatRoom(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="방 이름")
    description = models.TextField(max_length=200, blank=True, verbose_name="방 설명")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="created_rooms",
        verbose_name="방 생성자"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")
    is_active = models.BooleanField(default=True, verbose_name="활성 상태")
    max_members = models.PositiveIntegerField(default=100, verbose_name="최대 인원")
    is_private = models.BooleanField(default=False, verbose_name="비공개 방")
    password = models.CharField(max_length=20, blank=True, verbose_name="방 비밀번호")

    class Meta:
        verbose_name = "채팅방"
        verbose_name_plural = "채팅방들"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def total_messages(self):
        """총 메시지 수"""
        return self.messages.count()

class ChatRoomSettings(models.Model):
    """채팅방 설정"""
    room = models.OneToOneField(
        ChatRoom, 
        on_delete=models.CASCADE, 
        related_name="settings",
        verbose_name="채팅방"
    )
    allow_file_upload = models.BooleanField(default=True, verbose_name="파일 업로드 허용")
    allow_image_upload = models.BooleanField(default=True, verbose_name="이미지 업로드 허용")
    message_retention_days = models.PositiveIntegerField(
        default=30, 
        verbose_name="메시지 보관 기간(일)"
    )
    slow_mode_seconds = models.PositiveIntegerField(
        default=0, 
        verbose_name="슬로우 모드(초)",
        help_text="0이면 비활성화"
    )
    auto_delete_messages = models.BooleanField(
        default=False, 
        verbose_name="메시지 자동 삭제"
    )
    welcome_message = models.TextField(
        blank=True, 
        verbose_name="환영 메시지"
    )
    
    class Meta:
        verbose_name = "채팅방 설정"
        verbose_name_plural = "채팅방 설정들"
    
    def __str__(self):
        return f"{self.room.name} 설정"
    
class RoomMember(models.Model):
    """채팅방 멤버 관리"""
    room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE, 
        related_name="members",
        verbose_name="채팅방"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="joined_rooms",
        verbose_name="사용자"
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="입장일시")
    last_seen = models.DateTimeField(default=timezone.now, verbose_name="마지막 접속")
    is_admin = models.BooleanField(default=False, verbose_name="관리자 권한")
    nickname = models.CharField(max_length=30, blank=True, verbose_name="방 내 닉네임")
    
    class Meta:
        verbose_name = "방 멤버"
        verbose_name_plural = "방 멤버들"
        unique_together = ['room', 'user']  # 한 방에 같은 유저는 한 번만
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} in {self.room.name}"

class ChatMessage(models.Model):
    """채팅 메시지 모델"""
    MESSAGE_TYPES = [
        ('text', '일반 텍스트'),
        ('image', '이미지'),
        ('file', '파일'),
        ('system', '시스템 메시지'),
    ]
    
    room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE, 
        related_name="messages",
        verbose_name="채팅방"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="chat_messages",
        verbose_name="작성자"
    )
    content = models.TextField(verbose_name="메시지 내용")
    message_type = models.CharField(
        max_length=10, 
        choices=MESSAGE_TYPES, 
        default='text',
        verbose_name="메시지 타입"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일시")
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name="수정일시")
    is_deleted = models.BooleanField(default=False, verbose_name="삭제 여부")
    file_url = models.URLField(blank=True, verbose_name="파일 URL")
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name="replies",
        verbose_name="답장 대상"
    )
    
    class Meta:
        verbose_name = "채팅 메시지"
        verbose_name_plural = "채팅 메시지들"
        ordering = ['created_at']
    
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
    