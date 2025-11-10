from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import ChatRoom, MessageReaction, PushSubscription, RoomMember, ChatMessage, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_online', 'last_activity', 'preferred_language']
    list_filter = ['is_online', 'preferred_language', 'last_activity']
    search_fields = ['user__username', 'bio']
@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description','is_active', 'created_at']
    list_filter = ['is_active', 'is_private', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at','total_messages']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('설정', {
            'fields': ('is_active', 'is_private', 'password', 'max_members')
        }),
        ('통계', {
            'fields': ('total_messages',), 
            'classes': ('collapse',)
        }),
        ('날짜', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RoomMember)
class RoomMemberAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'room', 'is_admin', 'joined_at', 'last_seen', 'is_currently_in_room', 'last_read_message']
    list_filter = ['is_admin', 'joined_at']
    search_fields = ['user__username', 'room__name', 'nickname', 'joined_at', 'last_seen', 'is_currently_in_room', 'last_read_message']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'room', 'content_preview', 'message_type', 'file_info', 'created_at']
    list_filter = ['message_type', 'is_deleted', 'created_at', 'room']
    search_fields = ['user__username', 'room__name', 'content', 'file_name']
    readonly_fields = ['created_at', 'edited_at', 'file_size_human']
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('room', 'user', 'message_type')
        }),
        ('메시지 내용', {
            'fields': ('content',),
            'description': '텍스트 메시지인 경우에만 사용됩니다.'
        }),
        ('파일/이미지 정보', {
            'fields': ('file', 'file_name', 'file_size', 'file_size_human'),
            'classes': ('collapse',),
            'description': '파일이나 이미지 메시지인 경우에만 사용됩니다.'
        }),
        ('답장 기능', {
            'fields': ('reply_to',),
            'classes': ('collapse',),
            'description': '다른 메시지에 대한 답장인 경우 설정됩니다.'
        }),
        ('읽음 상태', {
            'fields': ('unread_count', 'total_members_at_time'),
            'classes': ('collapse',),
            'description': '메시지 읽음 상태 관련 정보입니다.'
        }),
        ('메타 정보', {
            'fields': ('is_deleted', 'created_at', 'edited_at'),
            'classes': ('collapse',),
            'description': '메시지의 메타데이터 정보입니다.'
        }),
        ('추가 정보', {
            'fields': ('is_image', 'is_file'),
            'classes': ('collapse',),
            'description': '파일 타입에 대한 추가 정보입니다.'
        }),
    )
    
    def content_preview(self, obj):
        """내용 미리보기"""
        if obj.message_type in ['file', 'image']:
            return f"📎 {obj.file_name or '파일'}"
        elif obj.content:
            return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
        else:
            return "(내용 없음)"
    content_preview.short_description = "내용 미리보기"
    
    def file_info(self, obj):
        """파일 정보 표시"""
        if obj.message_type in ['file', 'image'] and obj.file:
            return f"{obj.file_name} ({obj.file_size_human})"
        return "-"
    file_info.short_description = "파일 정보"
    
    def get_readonly_fields(self, request, obj=None):
        """편집 시 읽기 전용 필드 동적 설정"""
        readonly = list(self.readonly_fields)
        if obj:  # 편집 모드
            readonly.extend(['message_type', 'file', 'file_name', 'file_size'])
        return readonly
    
    def get_fieldsets(self, request, obj=None):
        """메시지 타입에 따라 필드셋 동적 변경"""
        fieldsets = list(self.fieldsets)
        
        if obj and obj.message_type == 'text':
            # 텍스트 메시지인 경우 파일 관련 필드 숨기기
            fieldsets = [fs for fs in fieldsets if fs[0] != '파일/이미지 정보']
        elif obj and obj.message_type in ['file', 'image']:
            # 파일/이미지 메시지인 경우 내용 필드 숨기기
            fieldsets = [fs for fs in fieldsets if fs[0] != '메시지 내용']
            
        return fieldsets

@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'message', 'user', 'reaction_type', 'created_at']
    list_filter = ['reaction_type', 'created_at']
    search_fields = ['message__id', 'user__username', 'reaction_type']
    ordering = ['-created_at']

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'endpoint', 'p256dh', 'p256dh', 'created_at')
    search_fields = ('endpoint', 'user__username')
    list_filter = ('user', 'created_at')