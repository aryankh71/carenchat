# carenchat/asgi.py
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chatbox.routing import websocket_urlpatterns

# تنظیم متغیر محیطی
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carenchat.settings')

# لود کردن اپلیکیشن‌های جنگو
django.setup()

# تنظیمات ASGI
application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})