import json
import logging
from typing import Any
from django.db.models.query import QuerySet
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from rest_framework.decorators import api_view
from rest_framework import generics, views, status, serializers, parsers
from rest_framework.response import Response
from django.apps import apps as proj_apps
from .user_thread import UserThread
from .actor import Actor
from .models import Thread, ThreadSerializer, Assistant, AssistantSerializer


LOGGER = logging.getLogger(__name__)


class ThreadListView(generics.ListCreateAPIView):
    model = Thread
    serializer_class = ThreadSerializer

    def list(self, request):
        user_id = request.query_params.get('user', None)
        if (user_id is not None):
            queryset = Thread.objects.filter(user_id=user_id).order_by('-origin_date')[:10]
            serializer = ThreadSerializer(queryset, many=True)
            return Response(serializer.data)
        else:
            raise Response(serializers.ValidationError("No user was provided."))       

    def create (self, request, *args, **kwargs):
        user_id = request.data.get('user', None)
        if (user_id is not None):
            thread = UserThread.create_thread(user_id=user_id)
            return Response(ThreadSerializer(thread).data)
        else:
            raise Response(serializers.ValidationError("No user was provided."))           
    
class ThreadDetailView(generics.RetrieveUpdateDestroyAPIView):
    model = Thread
    serializer_class = ThreadSerializer
    
    def retrieve(self, request, *args, **kwargs):
        thread_id = kwargs['id']
        thread = Thread.objects.get(thread_id=thread_id)
        user_thread = UserThread(user_id=thread.user_id, thread_id=thread_id)
        serializer = ThreadSerializer(thread)
        return Response(serializer.data)
    
    def delete(self, request, *args, **kwargs):
        thread_id = kwargs['id']
        thread = Thread.objects.get(thread_id=thread_id)
        user_thread = UserThread(user_id=thread.user_id, thread_id=thread_id)
        user_thread.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    # updating a thread adds a new message to thread 
    # and waits/streams the response
    def update(self, request, *args, **kwargs):
        thread_id    = kwargs['id']
        user_id      = request.query_params.get('user', None)
        input        = request.query_params.get('input', None)
        actor_name   = request.query_params.get('actor', None)

        if thread_id.lower() == 'none':
            thread_id = None
        user_thread = UserThread(user_id=user_id, thread_id=thread_id)
        actor = proj_apps.get_app_config('genscene').get_actor(actor_name)
        responses = actor.get_responses(input=input, user_thread=user_thread)


class ActorListView(generics.ListCreateAPIView):
    model = Assistant
    serializer_class = AssistantSerializer

    def list (self, request):
        config = proj_apps.get_app_config('genscene')
        # need to call this here to sync the state database
        actors = config.get_actors()
        queryset = Assistant.objects.all()
        serializer = AssistantSerializer(queryset, many=True)
        return Response(serializer.data)
    
class ActorDetailView(generics.RetrieveAPIView):
    model = Assistant
    serializer_class = AssistantSerializer

    def retrieve(self, request, *args, **kwargs):
        actor_name = kwargs['name']
        config = proj_apps.get_app_config('genscene')
        # need to call this here to sync the state database
        actor = config.get_actor(actor_name)
        asst = Assistant.objects.get(actor_name=actor_name)
        serializer = AssistantSerializer(asst)
        return Response(serializer.data)


class PlainTextParser(parsers.BaseParser):
    media_type = 'text/plain'
    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()


class ChatView (generics.CreateAPIView):

    def create (self, request, *args, **kwargs):
        user_id = request.data.get('user', None)
        input = request.data.get('input', '')
        actor_name = request.data.get('actor', None)
        thread_id = request.data.get('thread', None)
        buffer_size = request.data.get('buffer_size', 1)
        LOGGER.info(f"ChatView.POST for input: {input}, user: {user_id}, actor: {actor_name}, thread_id: {thread_id}")

        user_thread = UserThread(user_id=user_id, thread_id=thread_id)
        actor: Actor = proj_apps.get_app_config('genscene').get_actor(actor_name)

        response_stream = actor.stream_responses(input=input, user_thread=user_thread, buffer_size=buffer_size)
        # response = StreamingHttpResponse(response_stream, content_type='text/markdown')
        response = StreamingHttpResponse(response_stream, content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response["thread_id"] = user_thread.thread_id
        response["actor"] = actor_name
        return response

        # response = actor.get_responses(input=input, user_thread=user_thread)
        # return JsonResponse({"messages": response, "thread_id": user_thread.thread_id})
    

