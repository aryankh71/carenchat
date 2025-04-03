from django.contrib import admin
from django.apps import apps
from chatbox.models import Chat,Message  # مدل Chat رو وارد می‌کنیم


def register_all_app_models():
    models_to_ignore = [
        'admin.LogEntry',
        'contenttypes.ContentType',
        'sessions.Session',
        'authtoken.TokenProxy',
        'authtoken.Token',
    ]

    for model in apps.get_models():
        try:
            if model._meta.label in models_to_ignore:
                continue
            else:
                # تعریف کلاس ModelAdmin به‌صورت پویا
                class TraderAdmin(admin.ModelAdmin):
                    list_display = [f.name for f in model._meta.fields]

                    # اضافه کردن قابلیت جستجو فقط برای مدل Chat
                    if model == Message:  # فقط برای مدل Chat اعمال می‌شه
                        search_fields = [
                            'chat__user1__username',  # جستجو بر اساس یوزرنیم user1
                            'chat__user2__username',  # جستجو بر اساس یوزرنیم user2
                            'chat__user1__phone',  # جستجو بر اساس شماره تماس user1
                            'chat__user2__phone',  # جستجو بر اساس شماره تماس user2
                        ]

                # ثبت مدل با کلاس TraderAdmin
                admin.site.register(model, TraderAdmin)

        except admin.sites.AlreadyRegistered:
            pass


register_all_app_models()