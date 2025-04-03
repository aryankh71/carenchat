from django.utils import timezone
from django.contrib.auth import get_user_model

class UpdateLastSeenMiddleware:
    def _init_(self, get_response):
        self.get_response = get_response

    def _call_(self, request):
        # اگه کاربر لاگین کرده، last_seen رو آپدیت کن
        if request.user.is_authenticated:
            User = get_user_model()
            User.objects.filter(id=request.user.id).update(last_seen=timezone.now())

        response = self.get_response(request)
        return response