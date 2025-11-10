from pywebpush import webpush, WebPushException
from django.conf import settings

def send_web_push(subscription_info, data):
    try:
        webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": "mailto:admin@example.com"
            }
        )
        return True
    except WebPushException as ex:
        print("Web push failed: {}", repr(ex))
        return False