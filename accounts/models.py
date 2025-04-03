from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.validators import RegexValidator
from django.db import models
from django.core.validators import FileExtensionValidator
# from django.contrib.auth import get_user_model
from django.conf import settings

class User(AbstractUser):
    last_seen = models.DateTimeField(null=True, blank=True)

    # شماره تماس: باید با +98 شروع شود و 10 رقم بعد از آن باشد.
    phone_regex = RegexValidator(
        regex=r'^\+98[0-9]{10}$',
        message="شماره تلفن باید با +98 شروع شده و شامل ۱۰ رقم بعدی باشد."
    )
    phone = models.CharField(
        max_length=13,
        unique=True,
        validators=[phone_regex],
        help_text="شماره تماس باید به فرمت +989123456789 باشد."
    )

    # ایمیل: باید با حرف انگلیسی شروع شده و فقط دامنه @gmail.com داشته باشد.
    email_regex = RegexValidator(
        regex=r'^[a-zA-Z][a-zA-Z0-9_.]*@gmail\.com$',
        message="ایمیل باید با حروف انگلیسی شروع شده و دامنه @gmail.com داشته باشد."
    )
    email = models.EmailField(
        unique=True,
        validators=[email_regex],
        blank=True,
        null=True
    )

    # یوزرنیم: باید با حروف انگلیسی شروع شود و شامل اعداد، نقطه، و آندرلاین باشد.
    username_regex = RegexValidator(
        regex=r'^[a-zA-Z][a-zA-Z0-9_.]*$',
        message="نام کاربری باید با حروف انگلیسی شروع شود و فقط شامل حروف، اعداد، نقطه و آندرلاین باشد."
    )
    username = models.CharField(
        max_length=50,
        unique=True,
        validators=[username_regex],
        blank=True,
        null=True,
        help_text="نام کاربری باید با حروف انگلیسی شروع شده و شامل اعداد، نقطه و آندرلاین باشد."
    )

    profile_photo = models.ImageField(
        upload_to='profile_pics/',
        default='profile_pics/person.png',
        null=True, blank=True,
        help_text="تصویر پروفایل خود را انتخاب کنید"
    )

    groups = models.ManyToManyField(Group, related_name="custom_user_set", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions_set", blank=True)

    USERNAME_FIELD = 'phone'  # ورود با شماره تلفن
    REQUIRED_FIELDS = ['username', 'email']  # فیلدهای ضروری برای ثبت نام

    def __str__(self):
        return self.phone




class AlbumPhoto(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='album_photo')
    photo = models.ImageField(
        upload_to='album_photos/',
        default='album_photos/person.png',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg','jpeg','png','gif'])
        ])
    uploaded_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.user.username} uploaded at {self.uploaded_at}"