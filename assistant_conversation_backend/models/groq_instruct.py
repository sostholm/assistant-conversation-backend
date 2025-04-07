from magentic import prompt, OpenaiChatModel
from .base_model import BaseAIModel, Actions
import os

class GroqInstruct(BaseAIModel):
    """
    OpenAI 4o model wrapper for the Magentic library.
    This class is used to interact with the OpenAI 4o model using the Magentic library.
    """

    def __init__(self):
        self.model = OpenaiChatModel(
            "meta-llama/llama-4-scout-17b-16e-instruct",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
        )

    async def _generate(self, prompt_text: str) -> Actions:

        @prompt(
            prompt_text,
            model=self.model
        )
        async def generate_message() -> Actions: ...

        return await generate_message()