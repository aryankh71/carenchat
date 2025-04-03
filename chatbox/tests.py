import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client
from channels.testing import WebsocketCommunicator
from chatbox.consumers import ChatConsumer
from chatbox.models import Message, BlockedUser

User = get_user_model()

# فیکسچرها
@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        phone="+989123456890",
        email="usera@gmail.com",
        username="user_a",
        password="Pass12345"
    )

@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        phone="+989123456790",
        email="userb@gmail.com",
        username="user_b",
        password="Pass12345"
    )

@pytest.fixture
def client():
    return Client()

# تست ورود با شماره تلفن
def test_login_with_phone(client, user_a):
    response = client.post(reverse('login'), {
        'username': '+989123456890',  # شماره تلفن user_a
        'password': 'Pass12345'
    })
    assert response.status_code == 302  # ریدایرکت به صفحه‌ی بعد از ورود
    assert response.wsgi_request.user.is_authenticated
    assert response.wsgi_request.user.username == 'user_a'

# تست دسترسی به صفحه‌ی چت
def test_access_chat_page(client, user_a, user_b):
    client.login(username='+989123456890', password='Pass12345')  # ورود با شماره تلفن
    response = client.get(reverse('chat', kwargs={'username': user_b.username}))
    assert response.status_code == 200
    assert 'other_user' in response.context
    assert response.context['other_user'].username == 'user_b'

# تست ارسال پیام
@pytest.mark.asyncio
async def test_send_message(user_a, user_b):
    # ایجاد یک ارتباط WebSocket برای user_a
    communicator_a = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{user_b.username}/")
    communicator_a.scope['user'] = user_a
    # تنظیم دستی url_route برای شبیه‌سازی رفتار واقعی
    communicator_a.scope['url_route'] = {
        'kwargs': {
            'username': user_b.username
        }
    }
    connected, _ = await communicator_a.connect()
    assert connected

    # ارسال پیام از user_a به user_b
    message_text = "سلام، خوبی؟"
    await communicator_a.send_json_to({
        'type': 'chat_message',
        'message': message_text
    })

    # دریافت پیام
    response = await communicator_a.receive_json_from()
    assert response['type'] == 'chat_message'
    assert response['text'] == message_text
    assert response['sender'] == user_a.username

    # بررسی ذخیره شدن پیام در دیتابیس
    message = Message.objects.filter(sender=user_a, receiver=user_b).first()
    assert message is not None
    assert message.text == message_text

    await communicator_a.disconnect()

# تست بلاک کردن کاربر
def test_block_user(client, user_a, user_b):
    client.login(username='+989123456890', password='Pass12345')  # ورود user_a
    response = client.post(reverse('block_user', kwargs={'username': user_b.username}))
    assert response.status_code == 200
    assert response.json()['status'] == 'success'

    # بررسی اینکه کاربر بلاک شده
    blocked = BlockedUser.objects.filter(blocker=user_a, blocked=user_b).exists()
    assert blocked

# تست آنبلاک کردن کاربر
def test_unblock_user(client, user_a, user_b):
    # ابتدا کاربر رو بلاک می‌کنیم
    BlockedUser.objects.create(blocker=user_a, blocked=user_b)
    client.login(username='+989123456890', password='Pass12345')  # ورود user_a
    response = client.post(reverse('unblock_user', kwargs={'username': user_b.username}))
    assert response.status_code == 200
    assert response.json()['status'] == 'success'  # فقط status رو بررسی کن

    # بررسی اینکه کاربر آنبلاک شده
    blocked = BlockedUser.objects.filter(blocker=user_a, blocked=user_b).exists()
    assert not blocked

# تست نمایش پیام‌ها بعد از بلاک
def test_messages_visible_after_block(client, user_a, user_b):
    # ایجاد چند پیام بین user_a و user_b
    Message.objects.create(sender=user_a, receiver=user_b, text="پیام ۱")
    Message.objects.create(sender=user_b, receiver=user_a, text="پیام ۲")

    # بلاک کردن user_b توسط user_a
    client.login(username='+989123456890', password='Pass12345')  # ورود user_a
    client.post(reverse('block_user', kwargs={'username': user_b.username}))

    # بررسی صفحه‌ی چت از دید user_a (بلاک‌کننده)
    response_a = client.get(reverse('chat', kwargs={'username': user_b.username}))
    assert response_a.status_code == 200
    assert len(response_a.context['messages']) == 2  # پیام‌ها باید نمایش داده بشن
    assert 'شما این کاربر را بلاک کرده‌اید' in response_a.content.decode()

    # بررسی صفحه‌ی چت از دید user_b (بلاک‌شده)
    client.logout()
    client.login(username='+989123456790', password='Pass12345')  # ورود user_b
    response_b = client.get(reverse('chat', kwargs={'username': user_a.username}))
    assert response_b.status_code == 200
    assert len(response_b.context['messages']) == 2  # پیام‌ها باید نمایش داده بشن
    assert 'شما توسط این کاربر بلاک شده‌اید' in response_b.content.decode()

# تست ریل‌تایم بودن بلاک (شبیه‌سازی WebSocket)
@pytest.mark.asyncio
async def test_block_realtime(user_a, user_b):
    # ایجاد ارتباط WebSocket برای user_b (کاربر بلاک‌شده)
    communicator_b = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{user_a.username}/")
    communicator_b.scope['user'] = user_b
    # تنظیم دستی url_route برای شبیه‌سازی رفتار واقعی
    communicator_b.scope['url_route'] = {
        'kwargs': {
            'username': user_a.username
        }
    }
    connected, _ = await communicator_b.connect()
    assert connected

    # شبیه‌سازی بلاک کردن user_b توسط user_a
    BlockedUser.objects.create(blocker=user_a, blocked=user_b)

    # ارسال پیام بلاک از طریق WebSocket (شبیه‌سازی رفتار ویو block_user)
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"user_status_{user_b.username}",
        {
            "type": "block_message",
            "blocker_username": user_a.username,
            "blocked_username": user_b.username,
        }
    )

    # دریافت پیام بلاک توسط user_b
    response = await communicator_b.receive_json_from()
    assert response['type'] == 'block_status'
    assert response['blocker_username'] == user_a.username
    assert response['blocked_username'] == user_b.username

    await communicator_b.disconnect()

# تست تنظیمات کاربر (مثلاً always_keep_unread)
def test_user_settings(client, user_a, user_b):
    client.login(username='+989123456890', password='Pass12345')  # ورود user_a
    response = client.get(reverse('settings'))
    assert response.status_code == 200

    # تغییر تنظیم always_keep_unread
    response = client.post(reverse('save_settings'), {
        'show_last_seen': True,
        'hide_online_status': False,
        'show_typing_status': True,
        'always_keep_unread': True
    }, content_type='application/json')
    assert response.status_code == 200
    assert response.json()['status'] == 'success'

    # بررسی اینکه تنظیمات ذخیره شده
    user_a.refresh_from_db()
    assert user_a.settings.always_keep_unread == True