# chatbox/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q
from asgiref.sync import sync_to_async
from django.utils import timezone
import time
import asyncio

# دیکشنری برای ذخیره وضعیت کاربران
online_users = {}  # {username: {"is_online": bool, "last_seen": timestamp}}

# دیکشنری برای ذخیره زمان آخرین فعالیت کاربران
user_activity_timers = {}  # {username: timestamp}

# زمان بی‌فعالیتی (به ثانیه)
INACTIVITY_TIMEOUT = 60  # 60 ثانیه


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # بررسی وجود user توی scope
        if 'user' not in self.scope or not self.scope['user'].is_authenticated:
            print("خطا: کاربر احراز هویت نشده است یا در scope وجود ندارد")
            await self.close()
            raise ValueError(
                "User not found in scope or not authenticated. Ensure AuthMiddlewareStack is configured correctly.")

        self.username = self.scope['url_route']['kwargs']['username'].strip()
        self.user = self.scope['user']

        # وارد کردن مدل‌ها و get_user_model داخل متد
        from django.contrib.auth import get_user_model
        from .models import Chat
        User = get_user_model()

        # استفاده از sync_to_async برای دسترسی به دیتابیس
        try:
            self.other_user = await sync_to_async(User.objects.get)(username=self.username)
        except User.DoesNotExist:
            print(f"خطا: کاربر مقابل با نام کاربری {self.username} پیدا نشد")
            await self.close()
            return

        # پیدا کردن یا ساختن چت
        chat_query = Chat.objects.filter(
            Q(user1=self.user, user2=self.other_user) |
            Q(user2=self.user, user1=self.other_user)
        )
        self.chat = await sync_to_async(chat_query.first)()

        if not self.chat:
            self.chat = await sync_to_async(Chat.objects.create)(user1=self.user, user2=self.other_user)

        self.room_group_name = f'chat_{self.chat.id}'
        self.user_status_group_name = f"user_status_{self.user.username}"

        # اضافه کردن کاربر به گروه چت
        print(f"ChatConsumer: اضافه کردن {self.user.username} به گروه {self.room_group_name}")
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # اضافه کردن کاربر به گروه وضعیت کاربر (برای پیام‌های بلاک)
        print(f"ChatConsumer: اضافه کردن {self.user.username} به گروه {self.user_status_group_name}")
        await self.channel_layer.group_add(self.user_status_group_name, self.channel_name)

        # اضافه کردن کاربر به گروه وضعیت عمومی
        print(f"ChatConsumer: اضافه کردن {self.user.username} به گروه user_status")
        await self.channel_layer.group_add("user_status", self.channel_name)

        # به‌روزرسانی وضعیت آنلاین
        if self.user.is_authenticated:
            online_users[self.user.username] = {
                "is_online": True,
                "last_seen": int(time.time())
            }
            user_activity_timers[self.user.username] = int(time.time())  # زمان آخرین فعالیت

            hide_online_status = await self.get_hide_online_status()
            is_online = not hide_online_status

            print(f"ChatConsumer: ارسال پیام user_status_message برای {self.user.username}")
            await self.channel_layer.group_send(
                "user_status",
                {
                    "type": "user_status_message",
                    "username": self.user.username,
                    "is_online": is_online,
                    "last_seen": online_users[self.user.username]["last_seen"]
                }
            )

            # شروع بررسی بی‌فعالیتی
            self.start_inactivity_check()

        # وقتی گیرنده متصل می‌شه، تمام پیام‌های ارسالی مخاطب که هنوز دیده نشده رو به "دیده شده" آپدیت می‌کنیم
        await self.mark_messages_as_read()

        await self.accept()

    async def disconnect(self, close_code):
        # حذف کاربر از گروه چت
        print(f"ChatConsumer: حذف {self.user.username} از گروه {self.room_group_name}")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # حذف کاربر از گروه وضعیت کاربر
        print(f"ChatConsumer: حذف {self.user.username} از گروه {self.user_status_group_name}")
        await self.channel_layer.group_discard(self.user_status_group_name, self.channel_name)

        # حذف کاربر از گروه وضعیت عمومی
        print(f"ChatConsumer: حذف {self.user.username} از گروه user_status")
        await self.channel_layer.group_discard("user_status", self.channel_name)

        # به‌روزرسانی وضعیت آفلاین
        if self.user.is_authenticated:
            online_users[self.user.username] = {
                "is_online": False,
                "last_seen": int(time.time())
            }
            if self.user.username in user_activity_timers:
                del user_activity_timers[self.user.username]

            print(f"ChatConsumer: ارسال پیام user_status_message (آفلاین) برای {self.user.username}")
            await self.channel_layer.group_send(
                "user_status",
                {
                    "type": "user_status_message",
                    "username": self.user.username,
                    "is_online": False,
                    "last_seen": online_users[self.user.username]["last_seen"]
                }
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        # به‌روزرسانی زمان آخرین فعالیت
        if self.user.is_authenticated:
            user_activity_timers[self.user.username] = int(time.time())

        if message_type == "chat_message":
            message_text = data['message']

            # وارد کردن مدل Message داخل متد
            from .models import Message

            # چک کردن حضور کاربر مقابل
            other_user_in_chat = await self.is_other_user_in_chat()
            print(f"حضور کاربر مقابل ({self.other_user.username}) در چت: {other_user_in_chat}")

            # چک کردن تنظیمات کاربر گیرنده (کاربر مقابل)
            always_keep_unread = await self.get_always_keep_unread(self.other_user)
            print(f"تنظیم always_keep_unread برای گیرنده ({self.other_user.username}): {always_keep_unread}")

            # ذخیره پیام توی دیتابیس با sync_to_async
            message = await sync_to_async(Message.objects.create)(
                chat=self.chat,
                sender=self.user,
                text=message_text,
                created_at=timezone.now(),
                is_read=(other_user_in_chat and not always_keep_unread)
            )

            print(f"پیام جدید ذخیره شد - message_id: {message.id}, is_read: {message.is_read}")

            # Convert timestamp to local time (Asia/Tehran)
            message.created_at = message.created_at.astimezone(timezone.get_default_timezone())
            await sync_to_async(message.save)()

            # Debug print to verify timestamp
            print(f"<==ارسال پیام: {message.created_at.strftime('%H:%M')}")

            # Prepare the message to send
            message_data = {
                'type': 'chat_message',
                'sender': self.user.username,
                'text': message_text,
                'created_at': message.created_at.strftime('%H:%M'),
                'message_id': message.id,
                'is_read': message.is_read,
                'receiver_always_keep_unread': always_keep_unread
            }
            print(f"داده ارسالی به کلاینت: {message_data}")

            # ارسال پیام به گروه
            print(f"ارسال پیام به گروه: {self.room_group_name}")
            await self.channel_layer.group_send(
                self.room_group_name,
                message_data
            )

        elif message_type == "typing":
            is_typing = data["is_typing"]
            show_typing_status = await self.get_show_typing_status()
            if show_typing_status:
                print(f"ارسال وضعیت تایپینگ به گروه {self.room_group_name}: {is_typing}")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "typing_message",
                        "username": self.user.username,
                        "is_typing": is_typing
                    }
                )

        elif message_type == "chat_opened":
            always_keep_unread = await self.get_always_keep_unread(self.user)
            print(f"chat_opened - تنظیم always_keep_unread برای {self.user.username}: {always_keep_unread}")
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_opened",
                    "username": self.user.username,
                    "always_keep_unread": always_keep_unread
                }
            )

        elif message_type == "block_message":
            blocker = self.user.username
            blocked = self.other_user.username  # کاربر مقابل
            action = data['action']  # 'block' یا 'unblock'

            print(f"ChatConsumer: دریافت block_message - blocker: {blocker}, blocked: {blocked}, action: {action}")

            # ارسال پیام به گروه چت بلاک‌کننده
            await self.channel_layer.group_send(
                f'chat_{self.chat.id}',  # گروه چت فعلی
                {
                    'type': 'block_message',
                    'blocker_username': blocker,
                    'blocked_username': blocked,
                    'action': action,
                }
            )

            # ارسال پیام به گروه چت کاربر بلاک‌شده
            from django.contrib.auth import get_user_model
            from .models import Chat
            User = get_user_model()
            blocked_user_chat = await sync_to_async(Chat.objects.filter)(
                Q(user1__username=blocked, user2__username=blocker) |
                Q(user2__username=blocked, user1__username=blocker)
            )
            blocked_chat = await sync_to_async(blocked_user_chat.first)()
            if blocked_chat:
                blocked_group_name = f'chat_{blocked_chat.id}'
                print(f"ارسال block_message به گروه {blocked_group_name}")
                await self.channel_layer.group_send(
                    blocked_group_name,
                    {
                        'type': 'block_message',
                        'blocker_username': blocker,
                        'blocked_username': blocked,
                        'action': action,
                    }
                )

    async def chat_message(self, event):
        print(f"داده دریافت‌شده برای ارسال به WebSocket: {event}")
        message_to_send = {
            'type': 'chat_message',
            'sender': event['sender'],
            'text': event['text'],
            'created_at': event['created_at'],
            'message_id': event['message_id'],
            'is_read': event['is_read'],
            'receiver_always_keep_unread': event['receiver_always_keep_unread']
        }
        print(f"پیام نهایی برای websocket: {message_to_send}")

        await self.send(text_data=json.dumps(message_to_send))

    async def user_status_message(self, event):
        print(f"ChatConsumer: مدیریت پیام user_status_message برای {event['username']}")
        username = event["username"]
        is_online = event["is_online"]
        last_seen = event["last_seen"]

        await self.send(text_data=json.dumps({
            "type": "user_status",
            "username": username,
            "is_online": is_online,
            "last_seen": last_seen
        }))

    async def typing_message(self, event):
        username = event["username"]
        is_typing = event["is_typing"]

        await self.send(text_data=json.dumps({
            "type": "typing",
            "username": username,
            "is_typing": is_typing
        }))

    async def chat_opened(self, event):
        print(f"chat_opened - دریافت پیام برای {event['username']}, always_keep_unread: {event['always_keep_unread']}")
        await self.send(text_data=json.dumps({
            "type": "chat_opened",
            "username": event["username"],
            "always_keep_unread": event["always_keep_unread"]
        }))

    async def block_message(self, event):
        print(f"ChatConsumer: مدیریت پیام block_message برای {event['blocked_username']}, action: {event['action']}")
        await self.send(text_data=json.dumps({
            'type': 'block_status',
            'blocker_username': event['blocker_username'],
            'blocked_username': event['blocked_username'],
            'action': event['action']  # اضافه کردن action (block یا unblock)
        }))

    @sync_to_async
    def get_hide_online_status(self):
        from .models import Settings
        try:
            settings = self.user.settings
        except Settings.DoesNotExist:
            settings = Settings.objects.create(user=self.user)
        print(f"get_hide_online_status برای {self.user.username}: {settings.hide_online_status}")
        return settings.hide_online_status

    @sync_to_async
    def get_show_typing_status(self):
        from .models import Settings
        try:
            settings = self.user.settings
        except Settings.DoesNotExist:
            settings = Settings.objects.create(user=self.user)
        print(f"get_show_typing_status برای {self.user.username}: {settings.show_typing_status}")
        return settings.show_typing_status

    @sync_to_async
    def get_always_keep_unread(self, user):
        from .models import Settings
        try:
            settings = user.settings
        except Settings.DoesNotExist:
            settings = Settings.objects.create(user=user)
        print(f"get_always_keep_unread برای {user.username}: {settings.always_keep_unread}")
        return settings.always_keep_unread

    async def is_other_user_in_chat(self):
        from channels.db import database_sync_to_async
        @database_sync_to_async
        def get_group_channels():
            return self.channel_layer.groups.get(self.room_group_name, set())

        group_channels = await get_group_channels()
        print(f"تعداد کانال‌ها در گروه {self.room_group_name}: {len(group_channels)}")
        return len(group_channels) > 1

    async def mark_messages_as_read(self):
        from .models import Message
        always_keep_unread = await self.get_always_keep_unread(self.user)
        print(f"mark_messages_as_read - تنظیم always_keep_unread برای {self.user.username}: {always_keep_unread}")

        if always_keep_unread:
            print(f"تنظیم always_keep_unread برای {self.user.username} فعال است، پیام‌ها خوانده‌نشده باقی می‌مانند")
            return

        messages = await sync_to_async(list)(Message.objects.filter(
            chat=self.chat,
            sender=self.other_user,
            is_read=False
        ))
        for message in messages:
            message.is_read = True
            await sync_to_async(message.save)()
            print(f"پیام {message.id} به عنوان دیده شده علامت‌گذاری شد")

    async def start_inactivity_check(self):
        while self.user.is_authenticated and self.user.username in user_activity_timers:
            await asyncio.sleep(10)
            if self.user.username not in user_activity_timers:
                break

            last_activity = user_activity_timers.get(self.user.username, 0)
            current_time = int(time.time())
            if current_time - last_activity > INACTIVITY_TIMEOUT:
                online_users[self.user.username] = {
                    "is_online": False,
                    "last_seen": current_time
                }
                print(f"ChatConsumer: کاربر {self.user.username} به دلیل بی‌فعالیتی آفلاین شد")
                await self.channel_layer.group_send(
                    "user_status",
                    {
                        "type": "user_status_message",
                        "username": self.user.username,
                        "is_online": False,
                        "last_seen": online_users[self.user.username]["last_seen"]
                    }
                )
                break

    async def settings_updated(self, event):
        print(f"settings_updated - تغییر تنظیمات برای {event['username']}, always_keep_unread: {event['always_keep_unread']}")
        await self.send(text_data=json.dumps({
            "type": "settings_updated",
            "username": event["username"],
            "always_keep_unread": event["always_keep_unread"]
        }))


class UserStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.group_name = 'user_status'
        self.user_group_name = f"user_status_{self.user.username}"

        print(f"UserStatusConsumer: اضافه کردن {self.user.username} به گروه {self.group_name}")
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        await self.accept()

        # به‌روزرسانی وضعیت کاربر در دیتابیس
        if self.user.is_authenticated:
            from .models import Settings
            settings, created = await sync_to_async(Settings.objects.get_or_create)(user=self.user)
            settings.is_online = True
            await sync_to_async(settings.save)()

            print(f"UserStatusConsumer: ارسال پیام user_status_message برای {self.user.username}")
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_status_message',
                    'username': self.user.username,
                    'is_online': True,
                    'last_seen': int(time.time()),
                }
            )

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            from .models import Settings
            settings = await sync_to_async(Settings.objects.get)(user=self.user)
            settings.is_online = False
            settings.last_seen = timezone.now()
            await sync_to_async(settings.save)()

            print(f"UserStatusConsumer: ارسال پیام user_status_message (آفلاین) برای {self.user.username}")
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_status_message',
                    'username': self.user.username,
                    'is_online': False,
                    'last_seen': int(settings.last_seen.timestamp()),
                }
            )

        print(f"UserStatusConsumer: حذف {self.user.username} از گروه {self.group_name}")
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    async def user_status_message(self, event):
        print(f"UserStatusConsumer: مدیریت پیام user_status_message برای {event['username']}")
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'username': event['username'],
            'is_online': event['is_online'],
            'last_seen': event['last_seen'],
        }))

    async def block_message(self, event):
        print(f"UserStatusConsumer: مدیریت پیام block_message برای {event['blocked_username']}, action: {event['action']}")
        await self.send(text_data=json.dumps({
            'type': 'block_status',
            'blocker_username': event['blocker_username'],
            'blocked_username': event['blocked_username'],
            'action': event['action']  # اضافه کردن action (block یا unblock)
        }))