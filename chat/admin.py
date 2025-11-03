from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import ChatRoom, RoomMember, ChatMessage, UserProfile


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'description','is_active', 'created_at']
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
    list_display = ['user', 'room', 'is_admin', 'joined_at']
    list_filter = ['is_admin', 'joined_at']
    search_fields = ['user__username', 'room__name', 'nickname']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'content_preview', 'message_type', 'created_at']
    list_filter = ['message_type', 'is_deleted', 'created_at']
    search_fields = ['user__username', 'room__name', 'content']
    readonly_fields = ['created_at', 'edited_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "내용 미리보기"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_online', 'last_activity', 'preferred_language']
    list_filter = ['is_online', 'preferred_language', 'last_activity']
    search_fields = ['user__username', 'bio']
