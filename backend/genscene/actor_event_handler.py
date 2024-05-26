import time
import io
from abc import ABC, abstractmethod
from django.db import transaction
from typing import Dict, List, Any
from typing_extensions import override
import base64
import json

from openai.types.beta.threads import ImageFile, Text
from openai.types.beta.threads.runs.run_step import RunStep
from .user_thread import UserThread
from .return_message import ReturnItem
from .actor import Actor
from openai import OpenAI, AssistantEventHandler
from queue import Queue
import logging
import threading

LOGGER = logging.getLogger(__name__)

class ActorEventHandler(AssistantEventHandler):    

    openai_client: OpenAI
    message_queue: Queue
    thread_id: str

    def __init__(self, openai_client: OpenAI, thread_id: str, message_queue: Queue, actor: Actor) -> None:
        self.openai_client = openai_client
        self.thread_id = thread_id
        self.message_queue = message_queue
        self.actor = actor
        super().__init__()      

    @override
    def on_end(self) -> None:
        self.message_queue.put(None)

    # @override
    # def on_text_created(self, text) -> None:
    #     #self.producer.send(' ')
    #     #print(f"\nassistant > ", end="", flush=True)
    #     pass

    @override
    def on_text_delta(self, delta, snapshot):
        self.message_queue.put(delta.value)

    @override
    def on_text_done(self, text: Text) -> None:
        self.message_queue.put('\n')

    @override
    def on_image_file_done(self, image_file: ImageFile) -> None:
        print(f"on_image_file_done: {image_file.file_id}")
        item = ReturnItem.from_image_file(type='image_file', 
                                          role="assistant", 
                                          openai_client=self.openai_client, 
                                          file_id=image_file.file_id)
        # terminate with a pipe character
        self.message_queue.put(item.value+'|')
    
    @override
    def on_run_step_created(self, run_step: RunStep) -> None:
       self.run_id = run_step.run_id
       self.run_step = run_step

    # @override
    # def on_tool_call_created(self, tool_call):
    #     pass

    @override
    def on_tool_call_done(self, tool_call) -> None:

        current_run = self.openai_client.beta.threads.runs.retrieve(
           thread_id=self.thread_id,
           run_id=self.run_id
        )

        if (current_run.status == "requires_action"):
          if (tool_call.type == "function"):
              tool_id = tool_call.id
              func_name = tool_call.function.name
              arguments = json.loads(tool_call.function.arguments)
              # LOGGER.info(f"Calling function > {tool_id} {func_name} {arguments}")
              output_json = self.actor.call_function(func_name, arguments)
              with self.openai_client.beta.threads.runs.submit_tool_outputs_stream(
                   thread_id=self.thread_id,
                   run_id=self.run_id,
                   tool_outputs=[{
                       "tool_call_id": tool_id,
                       "output": output_json,
                   }],
                   event_handler=ActorEventHandler(
                        openai_client=self.openai_client,
                        thread_id=self.thread_id,
                        message_queue=self.message_queue,
                        actor=self.actor
                   )
               ) as stream:
                 stream.until_done() 
          else:
              LOGGER.error(f"Unhandled tool call type: {tool_call.type}")
        else:
            LOGGER.info(f"Run status is not requires_action: {current_run.status}")


