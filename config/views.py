from django.http import HttpRequest
from typing import Dict

def dashboard_callback(request: HttpRequest, context) -> Dict:
    return context
