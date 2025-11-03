from django.urls import path
from . import views

urlpatterns = [
    # path("", views.index, name="index"),
    # path("<str:room_name>/", views.room, name="room"),

    path("api/auth/login/", views.LoginAPIView.as_view(), name="api_login"),
    path("api/auth/logout/", views.LogoutAPIView.as_view(), name="api_logout"),
    path("api/auth/profile/", views.UserProfileAPIView.as_view(), name="api_profile"),

    path("api/rooms/", views.RoomListAPIView.as_view(), name="api_room_list"),
    path("api/my-rooms/", views.MyRoomsAPIView.as_view(), name="api_user_room_list"),
    path("api/rooms/create/", views.RoomCreateAPIView.as_view(), name="api_room_create"),
    path("api/stats/", views.RoomStatsAPIView.as_view(), name="api_room_stats"),
    path("api/rooms/delete/<int:room_id>/", views.RoomDeleteAPIView.as_view(), name="api_room_delete"),
    path("api/rooms/<str:room_name>/messages/", views.GetMessageAPIView.as_view(), name="api_message_list"),
    path("api/rooms/<str:room_name>/join/", views.JoinRoomAPIView.as_view(), name="api_room_join"),
    path("api/rooms/<str:room_name>/leave/", views.LeaveRoomAPIView.as_view(), name="api_room_leave"),
    path('api/rooms/<str:room_name>/info/', views.RoomInfoAPIView.as_view(), name='room_info'),
    path("api/rooms/<str:room_name>/mark-read/", views.MarkAsReadAPIView.as_view(), name="api_mark_read"),
    path("api/rooms/<str:room_name>/disconnect/", views.DisconnectRoomAPIView.as_view(), name="api_room_disconnect"),
]