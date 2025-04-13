from openai import OpenAI
from .base_model import BaseAIModel, Actions
from .output_parsing import parse_llm_output_to_actions
import asyncio

client = OpenAI()

class OpenAI4oMini:
    """
    OpenAI 4o model wrapper for the Magentic library.
    This class is used to interact with the OpenAI 4o model using the Magentic library.
    """

    def __init__(self):
        pass

    async def _generate(self, instructions: str, message, known_agent_names: list) -> Actions:

        response = None
        
        try:
            # Run the synchronous function in a separate thread without blocking the event loop
            response = await asyncio.to_thread(
                client.responses.create,
                model="gpt-4o-mini-2024-07-18",
                instructions=instructions,
                input=message
            )
            response = response.output_text
        except Exception as e:
            response = f"Error occurred while processing the message: {e}"

        return parse_llm_output_to_actions(response, known_agent_names=known_agent_names)