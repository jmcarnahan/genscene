from openai import OpenAI

import os

class OpenAIConfig:

    def client(self):
        return OpenAI(
            api_key=os.environ.get(
                "OPENAI_API_KEY", 
                "<your OpenAI API key is not set as env var>"
            ),
        )

    def deployment(self):
        return os.environ.get(
            "OPENAI_MODEL",
            "<your OpenAI model deployment is not set as env var>",
        )
