from django.db.models import Model, ImageField, CharField, ForeignKey, ManyToManyField, FileField, BinaryField, BooleanField, CASCADE
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    photo = ImageField()
    description = CharField(max_length=100)


class Media(Model):
    file = FileField()


class Message(Model):
    author = ForeignKey(to=User, on_delete=CASCADE, related_name="author", null=True, blank=True)
    target = ForeignKey(to=User, on_delete=CASCADE, related_name="target", null=True, blank=True)

    text = CharField(max_length=1000)

    mediafiles = ManyToManyField(Media)


class Chat(Model):
    name = CharField(max_length=100)
    description = CharField(max_length=100)

    users = ManyToManyField(User)
    messanges = ManyToManyField(Message)


class AudioChunk(Model):
    target = ForeignKey(to=User, on_delete=CASCADE, related_name="target_user", null=True, blank=True)
    data = BinaryField()


class Call(Model):
    first_user = ForeignKey(to=User, on_delete=CASCADE, related_name="user_one", null=True, blank=True)
    second_user = ForeignKey(to=User, on_delete=CASCADE, related_name="user_two", null=True, blank=True)

    accepted = BooleanField(default=None, null=True, blank=True)
