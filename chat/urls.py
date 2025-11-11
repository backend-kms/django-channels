from django.urls import path
from . import views

urlpatterns = [
    # path("", views.index, name="index"),
    # path("<int:room_id>/", views.room, name="room"),

    path("api/auth/login/", views.LoginAPIView.as_view(), name="api_login"),
    path("api/auth/logout/", views.LogoutAPIView.as_view(), name="api_logout"),
    path("api/auth/profile/", views.UserProfileAPIView.as_view(), name="api_profile"),

    path("api/rooms/", views.RoomListAPIView.as_view(), name="api_room_list"),
    path("api/my-rooms/", views.MyRoomsAPIView.as_view(), name="api_user_room_list"),
    path("api/rooms/create/", views.RoomCreateAPIView.as_view(), name="api_room_create"),
    path("api/stats/", views.RoomStatsAPIView.as_view(), name="api_room_stats"),
    path("api/rooms/delete/<int:room_id>/", views.RoomDeleteAPIView.as_view(), name="api_room_delete"),
    path("api/rooms/<int:room_id>/messages/", views.GetMessageAPIView.as_view(), name="api_message_list"),
    path("api/rooms/<int:room_id>/join/", views.JoinRoomAPIView.as_view(), name="api_room_join"),
    path("api/rooms/<int:room_id>/leave/", views.LeaveRoomAPIView.as_view(), name="api_room_leave"),
    path('api/rooms/<int:room_id>/info/', views.RoomInfoAPIView.as_view(), name='room_info'),
    path("api/rooms/<int:room_id>/mark-read/", views.MarkAsReadAPIView.as_view(), name="api_mark_read"),
    path("api/rooms/<int:room_id>/disconnect/", views.DisconnectRoomAPIView.as_view(), name="api_room_disconnect"),
    path('api/messages/<int:message_id>/reaction/', views.CreateReactionAPIView.as_view(), name='api_create_message_reaction'),
    path('api/messages/<int:message_id>/reactions/', views.ReactionAPIView.as_view(), name='api_message_reactions'),
    path('api/rooms/<int:room_id>/upload/', views.FileUploadAPIView.as_view(), name='file_upload'),

    path('test-notification/', views.notification_test, name='notification_test'),
    path('api/save-subscription/', views.SaveSubscriptionView.as_view(), name='save-subscription'),
]