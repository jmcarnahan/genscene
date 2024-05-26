from pydantic import BaseModel
import json
import io
import base64
from typing import List
from openai.types.beta.threads import ImageFile
from openai.types.beta.threads import Text
from openai.types.beta.threads import Message, MessageContent
from openai import OpenAI
import logging

LOGGER = logging.getLogger(__name__)


class ReturnItem(BaseModel):
    
  type: str
  role: str
  value: str

  @classmethod
  def from_text(cls, type: str, role: str, value: str) -> 'ReturnItem':
    return ReturnItem(type=type, role=role, value=value)

  @classmethod
  def from_image_file(cls, type: str, role: str, openai_client: OpenAI, file_id: str) -> 'ReturnItem':
    LOGGER.info(f"Loading image file: {file_id} using openai_client: {openai_client}")
    response_content = openai_client.files.content(file_id)
    data_in_bytes = response_content.read()
    readable_buffer = io.BytesIO(data_in_bytes)
    img_src = 'data:image/png;base64,' + base64.b64encode(readable_buffer.getvalue()).decode()
    return ReturnItem(type=type, value=img_src, role=role)

  @classmethod
  def from_message_content(cls, role: str, openai_client: OpenAI, item: MessageContent) -> 'ReturnItem':
    if item.type == 'text':
      return ReturnItem.from_text(item.type, role, item.text.value)
    elif item.type == 'image_file':
      return ReturnItem.from_image_file(item.type, role, openai_client, item.image_file.file_id)
    else:
      raise ValueError(f"Unknown type {type}")

class ReturnMessage(BaseModel):

  items: List[ReturnItem]

  def json(self, **kwargs):
      return json.dumps([item.model_dump() for item in self.items], **kwargs)

  @classmethod
  def from_message_list(cls, openai_client: OpenAI, messages: List[Message]) -> 'ReturnMessage':
    return_messages = ReturnMessage(items=[])
    for message in messages:
      for item in message.content:
        return_messages.items.append(ReturnItem.from_message_content(message.role, openai_client, item))
    return return_messages
  
  def add_text(self, role: str, value: str):
    last_item: ReturnItem = None
    if len(self.items) > 0:
      last_item = self.items[-1]
      if last_item.type != 'text':
        last_item = ReturnItem.from_text('text', role, '')
        self.items.append(last_item)
        print(f"Adding text to new item: {value}")
      else:
        print(f"Adding text to existing item: {value}")
    else:
      last_item = ReturnItem.from_text('text', role, '')
      self.items.append(last_item)
      print(f"Adding text to new item: {value}")
    last_item.value += value

  def add_image_file(self, role: str, openai_client: OpenAI, file_id: str):
    print(f"Adding image file: {file_id}")
    self.items.append(ReturnItem.from_image_file('image_file', role, openai_client, file_id))


  
