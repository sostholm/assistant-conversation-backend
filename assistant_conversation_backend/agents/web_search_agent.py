from openai import OpenAI
from .base_agent import BaseAgent
from ..state import MAIN_AI_QUEUE
from ..data_models import AIMessage
import asyncio

client = OpenAI()

class WebSearchAgent(BaseAgent):
    """An AI agent that searches the internet for up-to-date information. Capable of retrieving real-time data, news, and information from various online sources.
    """

    async def ask(self, message: str, caller: str):
        
        response = None
        
        try:
            # Run the synchronous function in a separate thread without blocking the event loop
            response = await asyncio.to_thread(
                client.responses.create,
                model="gpt-4o",
                tools=[{"type": "web_search_preview"}],
                input=message
            )
            response = response.output_text
        except Exception as e:
            response = f"Error occurred while processing the message: {e}"

        await MAIN_AI_QUEUE.put(
            AIMessage(
                message=response + ", Remember to update Users on status. Remember to convert to news caster format.",
                from_user=self.name,
                to_user=caller,
            )
        )