from magentic import prompt
from .base_model import BaseAIModel, Actions
import os

class OpenAI4o:
    """
    OpenAI 4o model wrapper for the Magentic library.
    This class is used to interact with the OpenAI 4o model using the Magentic library.
    """

    def __init__(self):
        pass

    async def _generate(self, prompt_text: str) -> Actions:

        @prompt(
            prompt_text,
        )
        async def generate_message() -> Actions: ...

        return await generate_message()