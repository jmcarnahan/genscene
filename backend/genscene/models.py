from django.db import models
from rest_framework import serializers
from .user_thread import UserThread


# python manage.py makemigrations --empty genscene
# python manage.py makemigrations
# python manage.py migrate

# python manage.py flush --noinput


class Assistant(models.Model):
    
    actor_name   = models.CharField(max_length=200, primary_key=True)
    assistant_id = models.CharField(max_length=200, null=True)
    instructions = models.CharField(max_length=10000)
    description  = models.CharField(max_length=1000)
    
    def __str__(self):
        return "assistant"

class File(models.Model):
    actor_name  = models.CharField(max_length=200)
    file_id     = models.CharField(max_length=200)

    def __str__(self):
        return "file"
    
class Thread(models.Model):
    user_id     = models.CharField(max_length=200)
    thread_id   = models.CharField(max_length=200)
    current     = models.BooleanField(default=True)
    name        = models.CharField(max_length=100)
    # need the origin so that we can sort by date
    origin_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "thread"

class ThreadSerializer (serializers.ModelSerializer):
    messages = serializers.SerializerMethodField('get_messages')

    class Meta:
        model = Thread
        fields = ['name', 'thread_id', 'user_id', 'messages']

    def get_messages (self, obj):
        user_thread = UserThread(user_id=obj.user_id, thread_id=obj.thread_id)
        return user_thread.get_messages().json()
    
class AssistantSerializer (serializers.ModelSerializer):
    class Meta:
        model = Assistant
        fields = ['actor_name', 'assistant_id', 'instructions', 'description']
