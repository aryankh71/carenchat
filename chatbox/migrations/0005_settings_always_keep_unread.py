# Generated by Django 5.1.7 on 2025-04-01 13:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbox', '0004_alter_chat_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='settings',
            name='always_keep_unread',
            field=models.BooleanField(default=False, help_text='اگر فعال باشد، پیام\u200cها همیشه به\u200cصورت خوانده\u200cنشده باقی می\u200cمانند.'),
        ),
    ]
