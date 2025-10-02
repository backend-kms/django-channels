import threading
from django.shortcuts import redirect
from django.conf import settings
import logging

_thread_locals = threading.local()
logger = logging.getLogger(__name__)

def get_current_request():
    return getattr(_thread_locals, 'request', None)

class Admin404RedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404 and request.path.startswith('/admin/'):
            logger.warning(f"Admin 404 redirect: {request.path}")
            return redirect(settings.ADMIN_REDIRECT_URL)
        return response