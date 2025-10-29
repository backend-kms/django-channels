from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

unfold_settings = {
    "SITE_TITLE": 'Channels 관리자 페이지',
    "SITE_HEADER": 'Channels 관리자 페이지',
    "SITE_URL": "/",
    # "SITE_ICON": lambda request: static("icon.svg"),  # both modes, optimise for 32px height
    # "SITE_ICON": {
    #     "light": lambda request: static("icon-light.svg"),  # light mode
    #     "dark": lambda request: static("icon-dark.svg"),  # dark mode
    # },
    # "SITE_LOGO": lambda request: static("logo.svg"),  # both modes, optimise for 32px height
    # "SITE_LOGO": {
    #     "light": lambda request: static("logo-light.svg"),  # light mode
    #     "dark": lambda request: static("logo-dark.svg"),  # dark mode
    # },
    "SITE_SYMBOL": "chat",  # symbol from icon set
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("favicon.svg"),
        },
    ],
    "SHOW_HISTORY": True,  # show/hide "History" button, default: True
    "SHOW_VIEW_ON_SITE": True,  # show/hide "View on site" button, default: True
    # "ENVIRONMENT": "config.views.environment_callback",  # "Development", "Staging", "Production"
    # "ENVIRONMENT": ["Production", "danger", "info", "danger", "warning", "success"],
    "DASHBOARD_CALLBACK": "config.views.dashboard_callback",
    # "THEME": "dark", # Force theme: "dark" or "light". Will disable theme switcher
    "LOGIN": {
        # "image": lambda request: static("sample/login-bg.jpg"),
        # "redirect_after": lambda request: reverse_lazy("admin:APP_MODEL_changelist"),
    },
    # "STYLES": [
    #     lambda request: static("css/style.css"),
    # ],
    # "SCRIPTS": [
    #     lambda request: static("js/script.js"),
    # ],  # ff4a22
    "COLORS": {
        "primary": {
            "50": "255 242 237",
            "100": "255 229 218",
            "200": "255 204 183",
            "300": "255 178 148",
            "400": "255 153 112",
            "500": "255 127 77",
            "600": "254 92 43",
            "700": "235 80 32",
            "800": "217 67 21",
            "900": "198 55 11",
            "950": "179 41 0"
        },
    },
    "SIDEBAR": {
        "show_search": True,  # Search in applications and models names
        "show_all_applications": False,  # Dropdown with all applications and models
        "navigation": [
            {
                "title": _("사용자 관리"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("사용자"),
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        # "badge": "config.views.user_badge_callback",
                    },
                    {
                        "title": _("그룹"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                    {
                        "title": _("사용자 프로필"),
                        "icon": "account_circle",
                        "link": reverse_lazy("admin:chat_userprofile_changelist"),
                    },
                ],
            },
            {
                "title": _("채팅 관리"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("채팅방"),
                        "icon": "chat_bubble",
                        "link": reverse_lazy("admin:chat_chatroom_changelist"),
                        # "badge": "config.views.chatroom_badge_callback",
                    },
                    {
                        "title": _("채팅 메시지"),
                        "icon": "message",
                        "link": reverse_lazy("admin:chat_chatmessage_changelist"),
                    },
                    {
                        "title": _("방 멤버"),
                        "icon": "people",
                        "link": reverse_lazy("admin:chat_roommember_changelist"),
                    },
                    {
                        "title": _("채팅방 설정"),
                        "icon": "settings",
                        "link": reverse_lazy("admin:chat_chatroomsettings_changelist"),
                    },
                ],
            },
        ]
    }
}
