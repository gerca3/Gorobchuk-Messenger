from django.contrib import admin
from django.urls import path

from lewapp.views import index, download_media, get_favicon, group_test, login_user, \
    logout_user, register_user, create_group_chat, my_groups

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('download/', download_media),
    path('my_groups/', my_groups, name='group_test'),
    path('group_test/', group_test, name='group_test'),
    path('create_group_chat/', create_group_chat, name='create_group_chat'),
    path('favicon.ico', get_favicon),
    path('register/', register_user, name='register'),
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout')
]