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
import hashlib

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
    file_lock = threading.Lock()

    def __init__(self, openai_client, openai_model ) -> None:
        self.openai_client = openai_client
        self.openai_model  = openai_model

    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_description(self) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def get_instructions(self) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def get_tools(self) -> List[Any]:
        raise NotImplementedError

    def get_code_resource_files(self) -> Dict[str, io.BytesIO]:
        return {}
    
    def get_openai_client(self):
        return self.openai_client
    
    def hash_value (self, value: str | bytes) -> int:
        hash_object = hashlib.sha256()
        if isinstance(value, str):
            hash_object.update(value.encode())
        elif isinstance(value, bytes):
            hash_object.update(value)
        else:
            raise ValueError("Value must be a string or bytes")
        hex_digest = hash_object.hexdigest()
        return str(int(hex_digest, 16))

    # TODO: support non code files later
    def get_tools_resources(self) -> Dict[str, Any]:
        from .models import File
        self.file_lock.acquire()
        try:
            
            code_files: Dict[str: io.BytesIO] = self.get_code_resource_files()

            new_file_hashes  = {name: self.hash_value(value=file_bytes.getvalue()) 
                                for name, file_bytes in code_files.items()}

            curr_files = {file.name: file 
                          for file in File.objects.filter(actor_name=self.get_name())}

            # this will add or update the file in the database
            file_ids = []
            for name, hash in new_file_hashes.items():
                if name not in curr_files or curr_files[name].hash != hash:

                    # delete old file id 
                    if name in curr_files:
                        self.openai_client.files.delete(curr_files[name].file_id)
                        file.delete()

                    # create new file id
                    assistant_file = self.openai_client.files.create(
                        file=(name, code_files[name].getvalue(),),
                        purpose="assistants",
                    )

                    # create or update the file in the database
                    db_file, created = File.objects.get_or_create(
                        actor_name=self.get_name(),
                        name=name,
                        defaults={
                            'file_id': assistant_file.id,
                            'hash': hash
                        }
                    )

                    file_ids.append(db_file.file_id)

                else:
                    file_ids.append(curr_files[name].file_id)

            # need to delete any files that are not in the new list
            for name, file in curr_files.items():
                if name not in new_file_hashes:
                    self.openai_client.files.delete(file.file_id)
                    file.delete()

            file_ids.sort()
            return {
                "code_interpreter": {
                    "file_ids": file_ids
                }
            }
        
        except Exception as e:
            raise Exception(e)
        finally:
            self.file_lock.release()


    # try to get the assistant id from the django default database
    def get_assistant_id(self):
        from .models import Assistant
        self.asst_lock.acquire()
        try:

            instructions = self.get_instructions()
            description = self.get_description()
            tools = self.get_tools()
            tools_resources = self.get_tools_resources()
            hash = self.hash_value(value=f"{instructions}{description}{tools}{tools_resources}")
            LOGGER.debug(f"Actor[{self.get_name()}] hash: {hash}") 
            LOGGER.debug(f"Actor[{self.get_name()}] tools resources: {tools_resources}")

            db_assistant, created = Assistant.objects.get_or_create(
                actor_name=self.get_name(),
                defaults={
                    'instructions': self.get_instructions(),
                    'description': self.get_description(),
                    'hash': hash,
                    'assistant_id': None,
                }
            )
            if created:
                openai_assistant = self.openai_client.beta.assistants.create(
                    name=f"{self.get_name().title()} Assistant",
                    instructions=instructions,
                    tools=tools,
                    tool_resources=tools_resources,
                    model=self.openai_model,
                )
                db_assistant.assistant_id = openai_assistant.id
                db_assistant.save()
                LOGGER.info(f"Actor[{self.get_name()}] created new assistant in openai: {db_assistant.assistant_id}")
            else:
                if db_assistant.hash != hash:
                    self.openai_client.beta.assistants.update(
                        assistant_id=db_assistant.assistant_id,
                        name=f"{self.get_name().title()} Assistant",
                        instructions=instructions,
                        tools=tools,
                        tool_resources=tools_resources,
                        model=self.openai_model,
                    )                        
                    LOGGER.info(f"Actor[{self.get_name()}] updated assistant in openai: {db_assistant.assistant_id}")
                else:
                    LOGGER.info(f"Actor[{self.get_name()}] using existing assistant: {db_assistant.assistant_id}")
            return db_assistant.assistant_id
        except Exception as e:
            raise Exception(e)
        finally:
            self.asst_lock.release()

    def sync (self):
        assistant_id = self.get_assistant_id()
        return self

    def delete (self):
        self.asst_lock.acquire()
        try:
            from .models import Assistant
            assistant_id = self.get_assistant_id()
            existing_asst = Assistant.objects.select_for_update().filter(
                assistant_id=assistant_id, 
            )
            if existing_asst.exists():
                self.openai_client.beta.assistants.delete(assistant_id)
                existing_asst.delete()

                # delete all files associated with this actor
                from .models import File
                files = File.objects.filter(actor_name=self.get_name())
                for file in files:
                    self.openai_client.files.delete(file.file_id)
                    file.delete()

                return True
            else:
                raise Exception(f"Assistant: could not delete assistant")    
        except Exception as e:
            raise Exception(e)
        finally:
            self.asst_lock.release()    


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


