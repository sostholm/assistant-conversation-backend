from magentic import (
    prompt
)
from magentic.chat_model.message import Message
from pydantic import BaseModel, Field
from enum import Enum
from .tools.home_assistant_tools import ask_home_assistant
from .database import get_ai, AI as AI_model
from starlette.websockets import WebSocket

AI: AI_model = get_ai(1)

class Recipient(Enum):
    USER = "user"
    KEEVA_ASSISTANT = "keeva-assistant"
    HOME_ASSISTANT_AI_AGENT = "home_assistant_ai_agent"

class Action(BaseModel):
    message: str
    recipient: Recipient = Field(
        description="The recipient of the action. keeva_assistant is yourself!",
    )

class Agent():

    def __init__(self, base_prompt: str):
        self.base_prompt = base_prompt

    def generate(self, conversation: str) -> Action:

        full_prompt = self.base_prompt + "\n" + conversation

        @prompt(full_prompt)
        async def generate_message() -> Action: ...

        return generate_message()

def make_chat_log_entry(message: str, sender: Recipient, recipient: Recipient, conversation: str) -> str:
    conversation += sender.value + " says to " + recipient.value + ": " + message + "\n"
    return conversation


async def call_agent(message: str, conversation: str, websocket: WebSocket) -> str:

    chat_agent = Agent(AI.ai_base_prompt)

    conversation = make_chat_log_entry(message, Recipient.USER, Recipient.KEEVA_ASSISTANT, conversation)

    while True:
        
        action: Action = await chat_agent.generate(conversation)
        conversation = make_chat_log_entry(action.message, Recipient.KEEVA_ASSISTANT, action.recipient, conversation)
        
        print(Recipient.KEEVA_ASSISTANT.value + ": " + action.message)

        if action.recipient == Recipient.HOME_ASSISTANT_AI_AGENT:
            message = await ask_home_assistant(action.message)
            conversation = make_chat_log_entry(message, Recipient.HOME_ASSISTANT_AI_AGENT, Recipient.KEEVA_ASSISTANT, conversation)

        if action.recipient == Recipient.USER:
            await websocket.send_text(action.message)
            return conversation


# if __name__ == "__main__":
#     chat_loop()