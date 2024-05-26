import time
import io
from abc import ABC, abstractmethod
from django.db import transaction
from typing import Dict, List, Any
from typing_extensions import override
import base64
import json


from openai.types.beta.threads.runs.run_step import RunStep
from .user_thread import UserThread
from .return_message import ReturnItem
from openai import OpenAI, AssistantEventHandler
from queue import Queue
import logging
import threading

LOGGER = logging.getLogger(__name__)





#
# Abstract Actor
#
# This wraps the core interaction with the Assistants API
# Each user + actor combination have Assistant defined for them so they
# can use their own instructions. This might be overkill but a good place to start
#
class Actor(ABC):

    openai_client: OpenAI
    openai_model: str
    asst_lock = threading.Lock()

    def __init__(self, openai_client, openai_model ) -> None:
        self.openai_client = openai_client
        self.openai_model  = openai_model

    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_assistant_files(self) -> Dict[str, io.BytesIO]:
        raise NotImplementedError

    @abstractmethod
    def get_description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_tools_list(self) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_instructions(self, user_id) -> str:
        raise NotImplementedError

    def get_openai_client(self):
        return self.openai_client

    # get the files for this actor and user
    # try to get the file ids from the django default database
    def get_file_ids(self):

        from .models import File
        
        file_ids = [file.file_id for file in File.objects.filter(actor_name=self.get_name())]
        if (len(file_ids) == 0):
            for name, file_bytes in self.get_assistant_files().items():
                assistant_file = self.openai_client.files.create(
                    file=(name, file_bytes,),
                    purpose="assistants",
                )
                file = File.objects.create(
                    file_id=assistant_file.id,
                    actor_name=self.get_name(),
                )
                file_ids.append(file.file_id)
                LOGGER.info(f"Actor[{self.get_name()}] created file in openai: {file.file_id}") 
        else: 
            # print(f"State: actor[{actor_name}] user[{self.user_id}]: got file IDs from db") 
            pass
        return file_ids    


    # try to get the assistant id from the django default database
    def get_assistant_id(self):
        from .models import Assistant
        self.asst_lock.acquire()
        try:
            db_assistant, created = Assistant.objects.get_or_create(
                actor_name=self.get_name(),
                defaults={
                    'instructions': self.get_instructions(),
                    'description': self.get_description(),
                    'assistant_id': None
                }
            )
            if created:
                openai_assistant = self.openai_client.beta.assistants.create(
                    name=f"{self.get_name().title()} Assistant",
                    instructions=self.get_instructions(),
                    tools=self.get_tools_list(),
                    #file_ids=self.get_file_ids(),
                    model=self.openai_model,
                )
                db_assistant.assistant_id = openai_assistant.id
                db_assistant.save()
                LOGGER.info(f"Actor[{self.get_name()}] created assistant in openai: {db_assistant.assistant_id}")
            else:
                LOGGER.debug(f"Actor[{self.get_name()}] using existing assistant: {db_assistant.assistant_id}")
            return db_assistant.assistant_id
        except Exception as e:
            raise Exception(e)
        finally:
            self.asst_lock.release()

    def sync (self):
        assistant_id = self.get_assistant_id()
        return self

    def delete (self):
        with transaction.atomic():
            from .models import Assistant
            assistant_id = self.get_assistant_id()
            existing_asst = Assistant.objects.select_for_update().filter(
                assistant_id=assistant_id, 
            )
            if existing_asst.exists():
                self.openai_client.beta.assistants.delete(assistant_id)
                existing_asst.delete()
                return True
            else:
                raise Exception(f"Assistant: could not delete assistant")        

    # Get databse schema by reaching out to the database directly
    # return as a byte buffer of YAML format of schema
    # def get_schema_data (self, db_name):
    #     meta_buffer = 'tables:\n'
    #     conn = connections[db_name]
    #     with conn.cursor() as cursor:
    #         table_info = conn.introspection.get_table_list(cursor)
    #         table_names = [info.name for info in table_info]
    #         for table_name in table_names:
    #             meta_buffer += f"  - name: {table_name}\n"
    #             meta_buffer += "    columns:\n"
    #             fields = conn.introspection.get_table_description(cursor, table_name)
    #             for field in fields:
    #                 meta_buffer += f"      - name: {field.name}\n"
    #                 meta_buffer += f"        type: {field.data_type}\n"
    #     # print(f"meta data from database[{db_name}]:\n{meta_buffer}")
    #     bytes_buffer = io.BytesIO(meta_buffer.encode('utf-8'))
    #     bytes_buffer.seek(0)
    #     return bytes_buffer   

    # # return as a byte buffer of file defined by path
    # def get_file_data (self, file_path):     
    #     with open(file_path, 'r', encoding='utf-8') as file:
    #         file_content = file.read()
    #         # print(f"read in file[{file_path}]:\n{file_content}")
    #         file_content_bytes = file_content.encode('utf-8')
    #         bytes_buffer = io.BytesIO(file_content_bytes)
    #         bytes_buffer.seek(0) 
    #         return bytes_buffer


    def _create_message (self, input, user_thread):
        thread_name = input
        if (len(thread_name) > 20):
            thread_name = f"{thread_name[:20]} ..."

        user_thread.set_name(thread_name)
        thread_id = user_thread.get_thread_id()

        msg = self.openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=input,
        )
        return msg

    # Get the responses using the assistant for the given user
    # def get_responses (self, input, user_thread):
    #     LOGGER.info(f"Actor[{self.get_name()}] getting responses for input: {input}")
    #     msg = self._create_message(input=input, user_thread=user_thread)
    #     return self.wait_for_response(message=msg, user_thread=user_thread)


    def stream_responses (self, input, user_thread, instructions="", buffer_size:int = 1):
        LOGGER.info(f"Actor[{self.get_name()}] streaming responses for input: {input} with buffer size: {buffer_size}")
        message_queue = Queue()
        msg = self._create_message(input=input, user_thread=user_thread)
        from .actor_event_handler import ActorEventHandler
        handler = ActorEventHandler(
            openai_client=self.openai_client,
            thread_id=user_thread.get_thread_id(), 
            message_queue=message_queue,
            actor=self
        )
        with self.openai_client.beta.threads.runs.stream(
            thread_id=msg.thread_id,
            assistant_id=self.get_assistant_id(),
            instructions=instructions, # get additional instructions from the actor here
            event_handler=handler,
        ) as openai_stream:
            stream_thread: threading.Thread = threading.Thread(target=openai_stream.until_done)
            stream_thread.start()
            streaming = True
            while streaming:
                try:
                    message = message_queue.get()
                    if message is not None:
                        yield message
                    else: 
                        streaming = False       
                except EOFError:
                    streaming = False 
            message_queue.task_done()   
            stream_thread.join()
        LOGGER.info(f"Actor[{self.get_name()}] streaming complete") 

    def call_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        if hasattr(self, function_name):
            function = getattr(self, function_name)
            return function(**arguments)
        else:
            raise ValueError(f"Unknown method in actor: {function_name}")

        


    # def wait_for_response (self, message, user_thread):

    #     assistant_id = self.get_assistant_id()
    #     thread_id = message.thread_id

    #     run = self.openai_client.beta.threads.runs.create(
    #         thread_id=thread_id,
    #         assistant_id=assistant_id,
    #     )

    #     try:
    #         for i in range(100):
    #             run = self.openai_client.beta.threads.runs.retrieve(
    #                 thread_id=thread_id, run_id=run.id
    #             )
    #             match run.status:
    #                 case "completed":
    #                     responses = user_thread.get_messages(last_only=True)
    #                     return responses
    #                 case "failed":
    #                     raise Exception("Run failed")
    #                 case "expired":
    #                     raise Exception("Run expired")
    #                 case "cancelled":
    #                     raise Exception("Run cancelled")
    #                 case "requires_action":
    #                     self.call_actions(self.openai_client, thread_id, run)
    #                 case other:
    #                     if run.expires_at is not None:
    #                         time_remaining = run.expires_at - time.time()
    #                         # print(f"Time remaining: {time_remaining}")
    #                     LOGGER.info('waiting for run to finish')
    #                     time.sleep(5)
    #     except Exception as e:
    #         print(f"Actor ERROR: wait for run: {e}: {run}")
    #         return [{'value': 'Sorry, I cannot answer that question', 'role': 'error'}]

    # def get_instructions(self, user_state):
    #     return user_state.get_instructions(actor_name=self.get_name())

    # def set_instructions(self, user_state, instructions):
    #     config = proj_apps.get_app_config('genscene')
    #     assistant_id = user_state.get_assistant_id(actor_name=self.get_name())
    #     # update the assistant
    #     config.client.beta.assistants.update(
    #         assistant_id=assistant_id, instructions=instructions
    #     )
    #     # update the database
    #     from .models import Assistant
    #     Assistant.objects.filter(assistant_id=assistant_id).update(instructions=instructions)
    #     # update this user state
    #     user_state.set_instructions(actor_name=self.get_name(), 
    #                                 instructions=instructions)
    #     print(f"Config: actor[{self.get_name()}] assistant[{assistant_id}]: updated instructions")
