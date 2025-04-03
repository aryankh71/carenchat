from django.urls import path
from .views import home, contacts, edit_profile
from . import views

urlpatterns = [
    path('', home, name='home'),
    path('contacts/', contacts, name='contacts'),
    path('chat/<str:username>/', views.chat_view, name='chat'),
    path('chat/<str:username>/messages/', views.get_messages, name='get_messages'),
    path('get-unread-counts/', views.get_unread_counts, name='get_unread_counts'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('settings/', views.settings, name='settings'),
    path('get_user_status/<str:username>/', views.get_user_status, name='get_unread_status'),
    path('set-profile-photo/<int:photo_id>/', views.set_profile_photo, name='set_profile_photo'),
    path('delete_album_photo/<int:photo_id>/', views.delete_album_photo, name='delete_album_photo'),
    path('upload_photo/', views.upload_photo, name='upload_photo'),
    path('save_settings/', views.save_settings, name='save_settings'),
    path('get_user_settings/<str:username>/', views.get_user_settings, name='get_user_settings'),
    path('block_user/<str:username>/', views.block_user, name='block_user'),
    path('unblock_user/<str:username>/', views.unblock_user, name='unblock_user'),
    path('get_user_profile/<str:username>/', views.get_user_profile, name='get_user_profile'),
    path('blocked_users/', views.blocked_users_list, name='blocked_users'),
    # path('chat/<str:username>/get_messages_status/', views.get_messages_status, name='get_messages_status')
]
