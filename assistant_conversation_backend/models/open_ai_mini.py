from magentic import prompt, OpenaiChatModel
from .base_model import BaseAIModel, Actions
import os

model = OpenaiChatModel("gpt-4.1-mini-2025-04-14")

class OpenAI4oMini:
    """
    OpenAI 4o model wrapper for the Magentic library.
    This class is used to interact with the OpenAI 4o model using the Magentic library.
    """

    def __init__(self):
        pass

    async def _generate(self, prompt_text: str) -> Actions:

        @prompt(
            prompt_text,
            model=model
        )
        async def generate_message() -> Actions: ...

        return await generate_message()