from django.db import models
from django.conf import settings
from django.db.models import Q
from django.contrib.auth import get_user_model




class Chat(models.Model):
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chats_as_user1")
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chats_as_user2")
    last_message = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = ['user1', 'user2'],
                name = 'unique_chat_user1_user2',
                condition = Q(user1__lt=models.F('user2'))
            ),
            models.UniqueConstraint(
                fields = ['user2', 'user1'],
                name = 'unique_chat_user2_user1',
                condition = Q(user2__lt=models.F('user1'))

            )
        ]

    # class Meta:
    #     unique_together = ('user1', 'user2')

    def __str__(self):
        return f"{self.user1.username} - {self.user2.username}"

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender}: {self.text[:20]}"


class Settings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='settings')
    show_last_seen = models.BooleanField(default=True)
    hide_online_status = models.BooleanField(default=False)
    show_typing_status = models.BooleanField(default=True)
    always_keep_unread = models.BooleanField(default=False,
                                             help_text="اگر فعال باشد، پیام‌ها همیشه به‌صورت خوانده‌نشده باقی می‌مانند.")
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"settings for {self.user.username}"

User = get_user_model()

class BlockedUser(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocked_by")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocked_users")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"