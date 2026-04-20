import json
from json import loads, dumps
from django.db.models import Q
from asgiref.sync import sync_to_async
from lewapp.models import Message, Media, User, Call
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from .models import Chat, Message, Media, User

class MessagesConsumer(AsyncWebsocketConsumer):
    @classmethod
    async def get_messages(self, user):
        messages_from_db = Message.objects.filter(target=user).select_related("author").prefetch_related("mediafiles")
        messages = []

        async for message in messages_from_db:
            media_data = [{"id": mediafile.id, "name": mediafile.file.name} for mediafile in message.mediafiles.all()]
            messages.append({"author": message.author.username, "text": message.text, "mediafiles": media_data})

        return messages


    async def send_messages(self, event):
        messages = event.get("messages")

        await self.send(text_data=dumps({
            "messages": messages
        }))


    async def connect(self):
        user = self.scope.get("user")
        user_id = user.id

        self.room_name = f"user_{user_id}_messages"

        messages = await self.get_messages(user)

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "send_messages",
                "messages": dumps(messages)
            }
        )


    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)


    async def receive(self, text_data=None, bytes_data=None):
        data = loads(text_data)

        text = data.get("text")

        media = data.get("media")
        mediafiles = []

        author_username = self.scope.get("user").username
        target_username = data.get("username")

        author = await User.objects.aget(username=author_username)
        target = await User.objects.aget(username=target_username)

        message = await Message.objects.acreate(author=author, target=target, text=text)

        for mediafile in media:
            filename = mediafile.get("filename")
            file_data = bytes(mediafile.get("data").values())

            file = ContentFile(file_data, name=filename)

            created_media = await Media.objects.acreate(file=file)
            mediafiles.append(created_media)

        await message.mediafiles.aset(mediafiles)

        messages = await self.get_messages(target)

        await self.channel_layer.group_send(
            f"user_{target.id}_messages",
            {
                "type": "send_messages",
                "messages": dumps(messages)
            }
        )


class CallsConsumer(AsyncWebsocketConsumer):
    @classmethod
    async def get_calls(self, user):
        calls_from_db = Call.objects.filter(Q(first_user=user) | Q(second_user=user), Q(accepted=None) | Q(accepted=True)).select_related("first_user").select_related("second_user")
        calls = []

        async for call in calls_from_db:
            if call.first_user == user:
                username = call.second_user.username
            elif call.second_user == user:
                username = call.first_user.username

            calls.append({"id": call.id, "user": username, "accepted": call.accepted})

        return calls


    async def get_pair_calls(self, first_user, second_user):
        calls_from_db = Call.objects.filter(Q(first_user=first_user, second_user=second_user) | Q(first_user=second_user, second_user=first_user)).select_related("first_user").select_related("second_user")
        calls = []

        async for call in calls_from_db:
            if call.first_user == first_user:
                username = call.second_user.username
            elif call.second_user == first_user:
                username = call.first_user.username

            calls.append({"id": call.id, "user": username, "accepted": call.accepted})

        return calls


    async def send_calls(self, event):
        calls = event.get("calls")

        await self.send(text_data=dumps({
            "calls": calls
        }))


    async def send_audio(self, event):
        audio = event.get("audio")

        await self.send(text_data=dumps({
            "audio": audio
        }))


    async def connect(self):
        user = self.scope.get("user")
        user_id = user.id

        self.room_name = f"user_{user_id}_calls"

        calls = await self.get_calls(user)

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "send_calls",
                "calls": dumps(calls)
            }
        )


    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)


    async def receive(self, text_data=None, bytes_data=None):
        data = loads(text_data)
        action = data.get("action")

        if action == "makeCall":
            first_user = self.scope.get("user")

            second_username = data.get("username")
            second_user = await User.objects.aget(username=second_username)

            old_calls = Call.objects.filter(Q(first_user=first_user, second_user=second_user) | Q(first_user=second_user, second_user=first_user))

            if not await old_calls.aexists():
                call = await Call.objects.acreate(first_user=first_user, second_user=second_user)

                calls = await self.get_calls(second_user)

                await self.channel_layer.group_send(
                    f"user_{second_user.id}_calls",
                    {
                        "type": "send_calls",
                        "calls": dumps(calls)
                    }
                )

        elif action == "callResponse":
            call_id = data.get("callId");
            accepted = data.get("accepted");

            call = await Call.objects.aget(id=call_id)

            user = self.scope.get("user")
            other_user = await sync_to_async(lambda: call.first_user if call.second_user == user else call.second_user)()

            other_user_id = other_user.id

            if not accepted:
                await call.adelete()
            else:
                call.accepted = True
                await call.asave()

            calls = await self.get_pair_calls(user, other_user)

            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "send_calls",
                    "calls": dumps(calls)
                }
            )

            calls_reversed = await self.get_pair_calls(other_user, user)

            await self.channel_layer.group_send(
                f"user_{other_user_id}_calls",
                {
                    "type": "send_calls",
                    "calls": dumps(calls_reversed)
                }
            )

        elif action == "sendAudio":
            first_user = self.scope.get("user")

            second_username = data.get("username")
            second_user = await User.objects.aget(username=second_username)

            calls = Call.objects.filter(Q(first_user=first_user, second_user=second_user) | Q(first_user=second_user, second_user=first_user))

            if await calls.aexists():
                await self.channel_layer.group_send(
                    f"user_{second_user.id}_calls",
                    {
                        "type": "send_audio",
                        "audio": data.get("chunk")
                    }
                )


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.chat_id}'

        self.chat = await self.get_chat_or_none(self.chat_id)
        if not self.chat or not await self.user_in_chat(self.user, self.chat):
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        messages = await self.get_chat_messages(self.chat)
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': messages
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'send_message':
            text = data.get('text', '')
            media_list = data.get('media', [])  # список файлов

            message = await self.create_message(self.user, text, media_list)
            if message:
                await self.add_message_to_chat(self.chat, message)

                message_data = {
                    'id': message.id,
                    'author': self.user.username,
                    'text': message.text,
                    'media': [{'id': m.id, 'name': m.file.name} for m in await self.get_message_media(message)],
                    'timestamp': str(message.id)  # можно заменить на datetime, если добавить поле
                }

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message_data
                    }
                )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))

    @database_sync_to_async
    def get_chat_or_none(self, chat_id):
        try:
            return Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            return None

    @database_sync_to_async
    def user_in_chat(self, user, chat):
        return chat.users.filter(id=user.id).exists()

    @database_sync_to_async
    def get_chat_messages(self, chat):
        messages = chat.messanges.all().order_by('id').select_related('author').prefetch_related('mediafiles')
        result = []
        for msg in messages:
            media = [{'id': m.id, 'name': m.file.name} for m in msg.mediafiles.all()]
            result.append({
                'id': msg.id,
                'author': msg.author.username,
                'text': msg.text,
                'media': media,
                'timestamp': str(msg.id)
            })
        return result

    @database_sync_to_async
    def create_message(self, author, text, media_list):
        message = Message.objects.create(author=author, text=text, target=None)
        media_objects = []
        for item in media_list:
            filename = item['filename']
            file_data = bytes(item['data'].values())
            file = ContentFile(file_data, name=filename)
            media = Media.objects.create(file=file)
            media_objects.append(media)
        message.mediafiles.set(media_objects)
        return message

    @database_sync_to_async
    def add_message_to_chat(self, chat, message):
        chat.messanges.add(message)

    @database_sync_to_async
    def get_message_media(self, message):
        return list(message.mediafiles.all())

class ChatsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        self.group_name = f"user_{self.user.id}_chats"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_chats_update(self, event):
        await self.send(text_data=dumps({
            'type': 'new_chat',
            'chat': event['chat']
        }))