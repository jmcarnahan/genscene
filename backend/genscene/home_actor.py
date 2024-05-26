from .actor import Actor
import io
from typing import Dict, Any, List



class HomeActor(Actor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    # overriden
    def get_name(self) -> str:
        return "home"

    # overriden
    def get_instructions(self) -> str:
        return """"You are helpful assistant on a wide range of topics. You will respond in a professional manner
to all questions and you will ask for clarity when the question is not clear. You will also provide a summary of the 
conversation at the end of the interaction."""
    
    # overriden
    def get_description(self) -> str:
        return "An example tool to interact with a plain chatbot"

    # overriden
    def get_assistant_files(self) -> Dict[str, io.BytesIO]:
        return {}
    
    # overriden
    def get_tools_list(self) -> List[Any]:
        return [
            {"type": "code_interpreter"},
        ]
    
    def call_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        raise NotImplementedError


