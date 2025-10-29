from django.urls import path
from . import views

urlpatterns = [
    # 기존 템플릿 뷰들 (테스트용)
    path("", views.index, name="index"),
    path("<str:room_name>/", views.room, name="room"),

    # API 엔드포인트들 (5개)
    path("api/rooms/", views.RoomListAPIView.as_view(), name="api_room_list"),
    path("api/rooms/create/", views.RoomCreateAPIView.as_view(), name="api_room_create"),
    path("api/room/<str:room_name>/", views.RoomDetailAPIView.as_view(), name="api_room_detail"),
    path("api/validate-room/", views.RoomValidationAPIView.as_view(), name="api_room_validation"),
    path("api/stats/", views.RoomStatsAPIView.as_view(), name="api_room_stats"),
]