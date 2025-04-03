from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Chat, Message, Settings, BlockedUser
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from accounts.forms import ProfileEditForm
from django.contrib import messages
from django.utils import timezone
from .consumers import online_users
from accounts.models import AlbumPhoto
import os
from django.db import transaction
import time
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
# from django.conf import settings


User = get_user_model()

@login_required
def home(request):
    User = get_user_model()

    request.user.last_seen = timezone.now()
    request.user.save()

    chats = Chat.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    users = User.objects.exclude(id=request.user.id)

    MAX_WORDS = 5  # حداکثر تعداد کلمات
    MAX_LENGTH = 30  # حداکثر طول کل متن

    for chat in chats:
        last_message = chat.messages.order_by('-created_at').first()
        other_user = chat.user2 if chat.user1 == request.user else chat.user1

        # متن آخرین پیام با کوتاه‌سازی
        if last_message:
            message_text = last_message.text
            words = message_text.split()
            if len(words) > MAX_WORDS:
                message_text = ' '.join(words[:MAX_WORDS]) + '...'
            if len(message_text) > MAX_LENGTH:
                message_text = message_text[:MAX_LENGTH - 3] + '...'
            chat.last_message = message_text
            chat.last_message_time = last_message.created_at.strftime('%H:%M')
            chat.last_message_timestamp = int(time.mktime(last_message.created_at.timetuple()))
            chat.last_message_sender = last_message.sender
        else:
            chat.last_message = None
            chat.last_message_time = None
            chat.last_message_timestamp = ""
            chat.last_message_sender = None

        chat.unread_count = chat.messages.filter(is_read=False).exclude(sender=request.user).count()
        chat.last_seen_timestamp = int(time.mktime(other_user.last_seen.timetuple())) if other_user.last_seen else ""

    return render(request, 'chatbox/home.html', {'chats': chats, 'users': users})

@login_required
def contacts(request):
    users = get_user_model().objects.exclude(id=request.user.id)
    context = {
        "users": users,
        "title": "لیست کاربران"
    }
    return render(request, 'chatbox/contacts.html', context)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from chatbox.models import Chat, Message, BlockedUser
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def chat_view(request, username):
    other_user = get_object_or_404(User, username=username)

    # پیدا کردن یا ساختن چت
    chat = Chat.objects.filter(
        Q(user1=request.user, user2=other_user) |
        Q(user2=request.user, user1=other_user)
    ).first()

    if not chat:
        chat = Chat.objects.create(user1=request.user, user2=other_user)

    # چک کردن وضعیت بلاک
    is_blocked_by_me = BlockedUser.objects.filter(
        blocker=request.user, blocked=other_user
    ).exists()  # آیا من این کاربر رو بلاک کردم؟

    is_blocked_by_other = BlockedUser.objects.filter(
        blocker=other_user, blocked=request.user
    ).exists()  # آیا این کاربر من رو بلاک کرده؟

    is_blocked = is_blocked_by_me or is_blocked_by_other  # آیا کلاً بلاک وجود داره (از هر طرف)؟
    # علامت‌گذاری پیام‌ها به‌عنوان خونده‌شده (فقط اگه بلاک نشده باشه)
    if not is_blocked:
        Message.objects.filter(
            chat=chat,
            sender=other_user,
            is_read=False
        ).update(is_read=True)

    # گرفتن پیام‌ها
    messages = chat.messages.all().order_by('created_at')

    # تنظیم timezone برای پیام‌ها
    for message in messages:
        if message.created_at.tzinfo is None:
            message.created_at = timezone.make_aware(message.created_at, timezone.get_default_timezone())
        else:
            message.created_at = message.created_at.astimezone(timezone.get_default_timezone())

    context = {
        'other_user': other_user,
        'chat': chat,
        'messages': messages,
        'is_blocked': is_blocked,  # برای چک کردن کلی بلاک
        'is_blocked_by_me': is_blocked_by_me,  # برای دکمه‌ی بلاک/آنبلاک
        'is_blocked_by_other': is_blocked_by_other,  # برای نمایش پیام "شما بلاک شده‌اید"
    }
    return render(request, 'chatbox/chat.html', context)

        # این دو ویو رو می‌تونی حذف کنی چون WebSocket جای Polling رو می‌گیره، ولی برای سازگاری اولیه نگه داشتم
@login_required
def get_messages(request, username):
    User = get_user_model()
    try:
        other_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'error': 'کاربر یافت نشد'}, status=404)

    chat = Chat.objects.filter(
        Q(user1=request.user, user2=other_user) |
        Q(user2=request.user, user1=other_user)
    ).first()

    if not chat:
        return JsonResponse({'messages': []})

    messages = chat.messages.all().order_by('created_at')
    messages_data = [
        {
            'sender': message.sender.username,
            'text': message.text,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for message in messages
    ]
    return JsonResponse({'messages': messages_data})
#
# @login_required
# def get_messages_status(request, username):
#     user = request.user
#     other_user = get_object_or_404(User, username=username)
#
#     chat = Chat.objects.filter(
#         Q(user1=user, user2=other_user) | Q(user2=user, user1=other_user)
#     ).filter()
#
#     if not chat:
#         return JsonResponse({'messages': []})
#
#     messages = Message.objects.filter(chat=chat).order_by('created_at')
#     messages_data = [
#         {
#             'id':messages.id,
#             'is_read':message.is_read
#         }
#         for message in messages
#     ]
#     return JsonResponse({'messages':messages_data})


@login_required
def edit_profile(request):
    if request.method == 'POST':
        print("POST request received for edit_profile")
        print("POST data:", request.POST)

        profile_form = ProfileEditForm(request.POST, instance=request.user)

        print("Profile form valid?", profile_form.is_valid())
        if not profile_form.is_valid():
            print("Profile form errors:", profile_form.errors)

        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'پروفایل شما با موفقیت بروزرسانی شد')
            return redirect('edit_profile')

    else:
        profile_form = ProfileEditForm(instance=request.user)

    album_photos = AlbumPhoto.objects.filter(user=request.user)

    return render(request, 'chatbox/edit_profile.html', {
        'profile_form': profile_form,
        'album_photos': album_photos
    })


@login_required
def upload_photo(request):
    if request.method == 'POST':
        print("Upload photo request received")
        print("FILES data:", request.FILES)

        if not request.FILES.get('photo'):
            print("No file provided in request")
            return JsonResponse({
                'success': False,
                'error': 'فایلی ارسال نشده است.'
            }, status=400)

        try:
            file = request.FILES['photo']
            print("File received:", file.name, "Size:", file.size)

            # اعتبارسنجی فرمت فایل
            if not file.content_type.startswith('image/'):
                print("Invalid file type:", file.content_type)
                return JsonResponse({
                    'success': False,
                    'error': 'لطفاً فقط فایل‌های تصویری آپلود کنید.'
                }, status=400)

            with transaction.atomic():  # استفاده از تراکنش برای اطمینان از کامل شدن عملیات
                has_photos = AlbumPhoto.objects.filter(user=request.user).exists()
                has_profile_photo = request.user.profile_photo.name != ''

                # ذخیره عکس توی دیتابیس با user=request.user
                print("Saving photo for user:", request.user.username)
                album_photo = AlbumPhoto(user=request.user, photo=file)
                album_photo.save()
                print("Photo saved successfully:", album_photo.photo.url)

                # اگه این اولین عکسه و پروفایل عکس نداره، به عنوان عکس پروفایل تنظیمش کن
                if not has_photos and not has_profile_photo:
                    print("Setting as profile photo")
                    if request.user.profile_photo:
                        if os.path.isfile(request.user.profile_photo.path):
                            os.remove(request.user.profile_photo.path)
                    request.user.profile_photo.save(file.name, file, save=True)

                # برگرداندن URL و آیدی عکس برای آپدیت گالری
                return JsonResponse({
                    'success': True,
                    'photo_url': album_photo.photo.url,
                    'photo_id': album_photo.id
                })
        except Exception as e:
            print("Error saving photo:", str(e))
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

    print("Invalid request method:", request.method)
    return JsonResponse({
        'success': False,
        'error': 'درخواست نامعتبر است.'
    }, status=400)


@login_required
def set_profile_photo(request, photo_id):
    if request.method == 'POST':  # پشتیبانی از درخواست AJAX
        try:
            with transaction.atomic():
                photo = AlbumPhoto.objects.get(id=photo_id, user=request.user)
                print("Setting profile photo for user:", request.user.username, "Photo ID:", photo_id)

                if request.user.profile_photo:
                    if os.path.isfile(request.user.profile_photo.path):
                        os.remove(request.user.profile_photo.path)
                with open(photo.photo.path, 'rb') as f:
                    request.user.profile_photo.save(photo.photo.name, f, save=True)

                return JsonResponse({
                    'success': True,
                    'message': 'تصویر پروفایل با موفقیت تغییر کرد',
                    'profile_photo_url': request.user.profile_photo.url
                })
        except AlbumPhoto.DoesNotExist:
            print("Photo not found for ID:", photo_id)
            return JsonResponse({
                'success': False,
                'error': 'عکس موردنظر یافت نشد'
            }, status=404)
        except Exception as e:
            print("Error setting profile photo:", str(e))
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    else:  # پشتیبانی از درخواست معمولی (برای سازگاری با کد قبلی)
        try:
            with transaction.atomic():
                photo = AlbumPhoto.objects.get(id=photo_id, user=request.user)
                if request.user.profile_photo:
                    if os.path.isfile(request.user.profile_photo.path):
                        os.remove(request.user.profile_photo.path)
                with open(photo.photo.path, 'rb') as f:
                    request.user.profile_photo.save(photo.photo.name, f, save=True)
                messages.success(request, 'تصویر پروفایل با موفقیت تغییر کرد')
        except AlbumPhoto.DoesNotExist:
            messages.error(request, 'عکس موردنظر یافت نشد')
        return redirect('edit_profile')


@login_required
def get_user_profile(request, username):
    try:
        user = User.objects.get(username=username)
        photos = user.album_photo.all().order_by('-uploaded_at')
        return JsonResponse({
            "username": user.username,
            "phone_number": user.phone,
            "email": user.email,
            "bio": user.bio if hasattr(user, 'bio') else None,
            "date_joined": user.date_joined.strftime('%Y-%m-%d') if user.date_joined else None,
            "profile_photo": user.profile_photo.url if user.profile_photo else None,
            "photos": [{"url": photo.photo.url, "uploaded_at": photo.uploaded_at.isoformat()} for photo in photos],
        })
    except User.DoesNotExist:
        return JsonResponse({"error": "کاربر پیدا نشد"}, status=404)


@login_required
def delete_album_photo(request, photo_id):
    try:
        photo = AlbumPhoto.objects.get(id=photo_id, user=request.user)
        if request.user.profile_photo and request.user.profile_photo.url == photo.photo.url:
            if os.path.isfile(request.user.profile_photo.path):
                os.remove(request.user.profile_photo.path)
            request.user.profile_photo = None
            request.user.save()
        photo.photo.delete()
        photo.delete()
        messages.success(request, 'عکس با موفقیت حذف شد')
    except AlbumPhoto.DoesNotExist:
        messages.error(request, 'عکس موردنظر یافت نشد')
    return redirect('edit_profile')




@login_required
def get_unread_counts(request):
    # chats = Chat.objects.filter(user1=request.user) | Chat.objects.filter(user2=request.user)
    chats = Chat.objects.filter(Q(user1=request.user) | Q(user2=request.user))

    unread_data = {}
    last_messages = {}
    last_message_senders = {}
    last_message_times = {}
    last_message_timestamps = {}
    profile_photos = {}

    MAX_WORDS = 5  # حداکثر تعداد کلمات
    MAX_LENGTH = 30  # حداکثر طول کل متن (می‌تونید تغییرش بدید)

    for chat in chats:
        other_user = chat.user2 if chat.user1 == request.user else chat.user1

        # تعداد پیام‌های خونده‌نشده
        unread_count = Message.objects.filter(
            chat=chat,
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        unread_data[other_user.username] = unread_count if unread_count > 0 else 0

        # متن آخرین پیام، فرستنده، ساعت و تایم‌استمپ
        last_message = Message.objects.filter(chat=chat).order_by('-created_at').first()
        if last_message:
            message_text = last_message.text
            words = message_text.split()

            # چک کردن تعداد کلمات
            if len(words) > MAX_WORDS:
                message_text = ' '.join(words[:MAX_WORDS]) + '...'
            # چک کردن طول کل متن (بعد از کوتاه کردن کلمات یا اگه کلمات کم باشه)
            if len(message_text) > MAX_LENGTH:
                message_text = message_text[:MAX_LENGTH - 3] + '...'

            last_messages[other_user.username] = message_text
            last_message_senders[other_user.username] = last_message.sender.username
            last_message_times[other_user.username] = last_message.created_at.strftime('%H:%M')
            last_message_timestamps[other_user.username] = int(time.mktime(last_message.created_at.timetuple()))

            if other_user.profile_photo:
                profile_photos[other_user.username] = other_user.profile_photo.url
            else:
                profile_photos[other_user.username] = "/static/chatbox/img/person.png"
        else:
            last_messages[other_user.username] = ""
            last_message_senders[other_user.username] = ""
            last_message_times[other_user.username] = ""
            last_message_timestamps[other_user.username] = ""
            profile_photos[other_user.username] = "/static/chatbox/img/person.png"

    return JsonResponse({
        'unread_counts': unread_data,
        'last_messages': last_messages,
        'last_message_senders': last_message_senders,
        'last_message_times': last_message_times,
        'last_message_timestamps': last_message_timestamps,
        'profile_photos': profile_photos
    })
# @login_required
# def get_unread_counts(request):
#     chats = Chat.objects.filter(user1=request.user) | Chat.objects.filter(user2=request.user)
#     unread_data = {}
#     last_messages = {}
#     last_message_senders = {}
#     last_message_times = {}
#     profile_photos = {}
#
#     for chat in chats:
#         other_user = chat.user2 if chat.user1 == request.user else chat.user1
#
#         # تعداد پیام‌های خونده‌نشده
#         unread_count = Message.objects.filter(
#             chat=chat,
#             is_read=False
#         ).exclude(
#             sender=request.user
#         ).count()
#         if unread_count > 0:
#             unread_data[other_user.username] = unread_count
#         else:
#             None
#
#         # متن آخرین پیام، فرستنده و زمان آن
#         last_message = Message.objects.filter(chat=chat).order_by('-created_at').first()
#         if last_message:
#             last_messages[other_user.username] = last_message.text
#             last_message_senders[other_user.username] = last_message.sender.username
#             last_message_times[other_user.username] = last_message.created_at.strftime('%H:%M')
#
#             if other_user.profile_photo:
#                 profile_photos[other_user.username] = other_user.profile_photo.url
#             else:
#                 profile_photos[other_user.username] = None
#
#     return JsonResponse({
#         'unread_counts': unread_data,
#         'last_messages': last_messages,
#         'last_message_senders': last_message_senders,
#         'last_message_times': last_message_times,
#         'profile_photos': profile_photos
#     })
# @login_required
# def get_unread_counts(request):
#     chats = Chat.objects.filter(user1=request.user) | Chat.objects.filter(user2=request.user)
#     unread_data = {}
#
#     for chat in chats:
#         other_user = chat.user2 if chat.user1 == request.user else chat.user1
#         unread_count = Message.objects.filter(
#             chat=chat,
#             is_read=False
#         ).exclude(
#             sender=request.user
#         ).count()
#         unread_data[other_user.username] = unread_count
#
#     return JsonResponse({'unread_counts': unread_data})


    # if request.method == "POST":
    #     show_last_seen = request.POST.get("show_last_seen") == "on"
    #     hide_online_status = request.POST.get("hide_online_status") == "on"
    #     show_typing_status = request.POST.get("show_typing_status") == "on"
    #     request.user.settings.show_last_seen = show_last_seen
    #     request.user.settings.hide_online_status = hide_online_status
    #     request.user.settings.show_typing_status = show_typing_status
    #     request.user.settings.save()
    #     return redirect('settings')
    # return render(request, "chatbox/settings.html", {})


@login_required
def get_user_status(request, username):
    try:
        user = User.objects.get(username=username)
        status = online_users.get(username, {"is_online": False, "last_seen": 0})
        settings = Settings.objects.get(user=user)
        return JsonResponse({
            'is_online': settings.is_online,
            'last_seen': settings.last_seen.timestamp() if settings.last_seen else None,
            'show_last_seen': user.settings.show_last_seen,
            'hide_online_status': user.settings.hide_online_status,
            'show_typing_status': user.settings.show_typing_status,

        })
    except User.DoesNotExist:
        return JsonResponse({"error": "کاربر پیدا نشد."}, status=404)

@login_required
def save_settings(request):
    if request.method == "POST":
        data = json.loads(request.body)
        always_keep_unread = data.get("always_keep_unread", False)
        show_last_seen = data.get("show_last_seen", True)
        hide_online_status = data.get("hide_online_status", False)
        show_typing_status = data.get("show_typing_status", True)

        # ذخیره تنظیمات
        settings, created = Settings.objects.get_or_create(user=request.user)
        settings.always_keep_unread = always_keep_unread
        settings.show_last_seen = show_last_seen
        settings.hide_online_status = hide_online_status
        settings.show_typing_status = show_typing_status
        settings.save()

        # ارسال پیام به گروه‌های چت مرتبط
        channel_layer = get_channel_layer()
        # پیدا کردن تمام چت‌های کاربر
        from .models import Chat
        chats = Chat.objects.filter(Q(user1=request.user) | Q(user2=request.user))
        for chat in chats:
            room_group_name = f'chat_{chat.id}'
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    "type": "settings_updated",
                    "username": request.user.username,
                    "always_keep_unread": always_keep_unread
                }
            )

        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)


@login_required
def settings(request):
    if not hasattr(request.user, 'settings'):
        Settings.objects.create(user=request.user)


    blocked_users = BlockedUser.objects.filter(blocker=request.user).select_related('blocked')

    return render(request, "chatbox/settings.html", {
        'settings': request.user.settings,
        'current_user': request.user,
        'blocked_users': blocked_users,
    })


@login_required
def get_user_settings(request, username):
    try:
        user = User.objects.get(username=username)
        settings, created = Settings.objects.get_or_create(user=user)
        return JsonResponse({
            'always_keep_unread': settings.always_keep_unread,
            'show_last_seen': settings.show_last_seen,
            'hide_online_status': settings.hide_online_status,
            'show_typing_status': settings.show_typing_status,
        })
    except User.DoesNotExist:
        return JsonResponse({'error': 'کاربر پیدا نشد'}, status=404)

@login_required
def block_user(request, username):
    if request.method != "POST":
        return JsonResponse({"status": "error", "error": "Method not allowed"}, status=405)

    try:
        user_to_block = User.objects.get(username=username)
        if user_to_block == request.user:
            return JsonResponse({"status": "error", "error": "Cannot block yourself"}, status=400)

        # ایجاد یا بررسی بلاک
        BlockedUser.objects.get_or_create(blocker=request.user, blocked=user_to_block)

        chat = Chat.objects.filter(
            Q(user1=request.user, user2=user_to_block) |
            Q(user2=request.user, user1=user_to_block)
        ).first()

        if not chat:
            return JsonResponse({"status": "error", "error": "Chat not found"}, status=404)

        # ارسال پیام WebSocket به هر دو کاربر (بلاک‌کننده و بلاک‌شونده)
        channel_layer = get_channel_layer()
        if not channel_layer:
            return JsonResponse({"status": "error", "error": "WebSocket channel layer not configured"}, status=500)

        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.id}",{
                "type": "block_message",
                "blocker_username": request.user.username,
                "blocked_username": user_to_block.username,
                "action": "block"
            }
        )

        async_to_sync(channel_layer.group_send)(
            f"user_status_{request.user.username}",{
                "type": "block_message",
                "blocker_username": request.user.username,
                "blocked_username": user_to_block.username,
                "action": "block"
            }
        )

        return JsonResponse({
            "status": "success",
            "blocker_username": request.user.username,
            "blocked_username": user_to_block.username,
            "action": "block"
        })
    except User.DoesNotExist:
        return JsonResponse({"status": "error", "error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "error": f"An unexpected error occurred: {str(e)}"}, status=500)

@login_required
def unblock_user(request, username):
    if request.method != "POST":  # اصلاح شرط
        print(f"تلاش ناموفق برای آنبلاک {username} توسط {request.user.username} - متد اشتباه")
        return JsonResponse({"status": "error", "error": "Method not allowed"}, status=405)

    print(f"آنبلاک {username} توسط {request.user.username} شروع شد")
    try:
        user_to_unblock = User.objects.get(username=username)
        if user_to_unblock == request.user:
            return JsonResponse({"status": "error", "error": "Cannot unblock yourself"}, status=400)

        BlockedUser.objects.filter(blocker=request.user, blocked=user_to_unblock).delete()
        print(f"آنبلاک {username} توسط {request.user.username} با موفقیت انجام شد")

        chat = Chat.objects.filter(
            Q(user1=request.user, user2=user_to_unblock) |
            Q(user2=request.user, user1=user_to_unblock)
        ).first()

        if not chat:
            return JsonResponse({"status": "error", "error": "Chat not found"}, status=404)

        channel_layer = get_channel_layer()
        if not channel_layer:
            return JsonResponse({"status": "error", "error": "WebSocket channel layer not configured"}, status=500)

        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.id}",
            {
                "type": "block_message",
                "blocker_username": request.user.username,
                "blocked_username": user_to_unblock.username,
                "action": "unblock"
            }
        )

        async_to_sync(channel_layer.group_send)(
            f"user_status_{user_to_unblock.username}",
            {
                "type": "block_message",
                "blocker_username": request.user.username,
                "blocked_username": user_to_unblock.username,
                "action": "unblock"
            }
        )

        async_to_sync(channel_layer.group_send)(
            f"user_status_{request.user.username}",
            {
                "type": "block_message",
                "blocker_username": request.user.username,
                "blocked_username": user_to_unblock.username,
                "action": "unblock"
            }
        )

        return JsonResponse({
            "status": "success",
            "blocker_username": request.user.username,
            "blocked_username": user_to_unblock.username,
            "message": f"{username} از بلاک خارج شد"
        })

    except User.DoesNotExist:
        return JsonResponse({"status": "error", "error": "User not found"}, status=404)
    except Exception as e:
        print(f"خطا در آنبلاک {username} توسط {request.user.username}: {str(e)}")
        return JsonResponse({"status": "error", "error": f"An unexpected error occurred: {str(e)}"}, status=500)


@login_required
def blocked_users_list(request):
    blocked_users = BlockedUser.objects.filter(blocker=request.user)
    return render(request, 'chatbox/blocked_users.html', {'blocked_users': blocked_users})