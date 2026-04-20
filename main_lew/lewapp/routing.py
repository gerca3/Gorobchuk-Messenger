from django.urls import re_path

from lewapp import consumers
from lewapp.consumers import MessagesConsumer, CallsConsumer, ChatsConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/$", MessagesConsumer.as_asgi()),
    re_path(r"ws/call/$", CallsConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<chat_id>\d+)/$', consumers.GroupChatConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<chat_id>\d+)/$', consumers.ChatsConsumer.as_asgi())
]