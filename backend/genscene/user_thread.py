from typing import List
from django.apps import apps as proj_apps
from django.db import transaction
from openai.types.beta.threads import Message
import base64
import logging
from .return_message import ReturnMessage

LOGGER = logging.getLogger(__name__)
DEFAULT_NAME = "New Thread"

class UserThread:

    # if thread_id is none: get the current thread or create one if necessary
    def __init__(self, user_id, thread_id=None) -> None:

        self.user_id = user_id
        if (thread_id is not None):
            self.thread_id = thread_id
        else:
            
            openai_client = proj_apps.get_app_config('genscene').get_client()
            from .models import Thread
            try:
                with transaction.atomic():
                    existing_thread = Thread.objects.select_for_update().filter(
                        user_id=self.user_id, 
                        current=True
                    )
                    if existing_thread.exists():
                        thread_id = existing_thread.first().thread_id
                        self.thread_id = thread_id
                    else: 
                        thread = openai_client.beta.threads.create()
                        Thread.objects.create(
                            thread_id=thread.id,
                            user_id=self.user_id,
                            name=DEFAULT_NAME,
                            current=True,
                        )
                        LOGGER.info(f"Thread: user[{self.user_id}]: lazy init thread in openai: {thread.id}")
                        self.thread_id = thread.id
            except Exception as e:
                LOGGER.error(f"Thread: user[{self.user_id}]: error getting current thread: {e}")
                raise Exception(e)


    @staticmethod
    def create_thread (user_id):
        openai_client = proj_apps.get_app_config('genscene').get_client()
        from .models import Thread

        openai_thread = openai_client.beta.threads.create()
        new_thread = Thread.objects.create(
            thread_id=openai_thread.id,
            user_id=user_id,
            name=DEFAULT_NAME,
        )
        LOGGER.info(f"Thread: user[{user_id}]: created thread in openai: {openai_thread.id}")
        return new_thread

    def get_thread_id(self):
        return self.thread_id
    

    def delete (self):
        with transaction.atomic():
            from .models import Thread
            existing_thread = Thread.objects.select_for_update().filter(
                thread_id=self.thread_id, 
            )
            if existing_thread.exists():
                openai_client = proj_apps.get_app_config('genscene').get_client()
                openai_client.beta.threads.delete(self.thread_id)
                existing_thread.delete()
                return True
            else:
                raise Exception(f"Thread: user[{self.user_id}]: could not delete thread")
        
    def set_name (self, name):
        # for now - only set if it is not already set
        from .models import Thread
        with transaction.atomic():
            thread = Thread.objects.select_for_update().filter(
                thread_id=self.thread_id
            )
            if thread.exists():
                existingName = thread.first().name
                if ((existingName == DEFAULT_NAME) or
                    (existingName.strip() == "")):
                    thread.update(name=name)
            else:
                raise Exception('Thread does not exist')


    def get_messages (self, last_only=False):   
        config = proj_apps.get_app_config('genscene')
        openai_client = config.get_client()
        messages: List[Message] = openai_client.beta.threads.messages.list(
            thread_id=self.thread_id
        )

        # Get all the messages till the last user message
        message_list: List[Message] = []
        for message in messages.data:
            # dont include the original request
            if (last_only and message.role == "user"):
                break
            message_list.append(message)

        # Reverse the messages to show the last user message first
        message_list.reverse()

        # Print the user or Assistant messages or images
        return ReturnMessage.from_message_list(openai_client=openai_client, messages=message_list)
    
        # response_list = []
        # for message in message_list:
        #     for item in message.content:
        #         LOGGER.info(f"item.type: {item.type}")
        #         if item.type == 'text':
        #             response_list.append({'type': item.type, 'value': item.text.value, 'role': message.role})
        #         elif item.type == 'image_file':
        #             response_content = config.client.files.content(
        #                 item.image_file.file_id
        #             )
        #             data_in_bytes = response_content.read()
        #             readable_buffer = io.BytesIO(data_in_bytes)
        #             img_src = 'data:image/png;base64,' + base64.b64encode(readable_buffer.getvalue()).decode()
        #             response_list.append({'type': item.type, 'value': img_src, 'role': message.role})

        # return response_list
    

