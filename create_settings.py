from django.contrib.auth import get_user_model
from chatbox.models import Settings

User=get_user_model()

for user in User.objects.all():
    if not hasattr(user, 'settings'):
        Settings.objects.create(user=user)