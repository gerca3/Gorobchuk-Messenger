from django.db.models.signals import post_save
from django.dispatch import receiver

from channels.layers import get_channel_layer

from asgiref.sync import async_to_sync

from json import dumps

from lewapp.models import Message, Call, Chat
from lewapp.consumers import MessagesConsumer, CallsConsumer


@receiver(post_save, sender=Message)
def notification_on_save(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()

        messages = async_to_sync(MessagesConsumer.get_messages)(instance.target)

        async_to_sync(channel_layer.group_send)(
            f"user_{instance.target.id}_messages",
            {
                "type": "send_messages",
                "messages": dumps(messages)
            }
        )


@receiver(post_save, sender=Call)
def notification_on_call_save(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()

        calls = async_to_sync(CallsConsumer.get_calls)(instance.second_user)

        async_to_sync(channel_layer.group_send)(
            f"user_{instance.second_user.id}_calls",
            {
                "type": "send_calls",
                "calls": dumps(calls)
            }
        )
@receiver(post_save, sender=Chat)
def notification_on_chat_created(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        chat_info = {
            'id': instance.id,
            'name': instance.name,
            'description': instance.description,
        }
        for user in instance.users.all():
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}_chats",
                {
                    "type": "send_chats_update",
                    "chat": chat_info
                }
            )