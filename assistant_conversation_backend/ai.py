from magentic import (
    prompt,
    OpenaiChatModel,
)
# from magentic.chat_model.message import Message
from pydantic import BaseModel, Field
from enum import Enum
from .tools.home_assistant_tools import ask_home_assistant
from .database import get_ai, AI as AI_model, add_or_update_conversation, DSN, Message
from .state import GLOBAL_STATE
from .data_models import IncommingMessage, AssistantState, Session, Recipient
import psycopg
from datetime import datetime
from typing import Optional, List

GLOBAL_STATE: AssistantState

AI: AI_model = get_ai(1)

# Intelligent Input Filtering

class IntelligentInputFiltering(BaseModel):
    speaking_to_assistant: bool

IntelligenInputFilterModel = OpenaiChatModel("gpt-4o-mini", temperature=0.1)


# Agent related classes
class Action(BaseModel):
    message: str
    recipient: Recipient = Field(
        description="The recipient of the action. keeva_assistant is yourself!",
    )
    device: Optional[str] = Field(
        description="The device to send the message to. (ONLY APPLIES TO USER RECIPIENTS)",
    )

class Agent():

    def __init__(self, base_prompt: str):
        self.base_prompt = base_prompt

    def generate(self, conversation: str) -> Action:
        
        connected_devices = ", ".join([session.device.location for session in GLOBAL_STATE.sessions.values()])

        full_prompt = self.base_prompt + f"\nConnected devices are: {connected_devices}" + "\n" + conversation

        @prompt(full_prompt)
        async def generate_message() -> Action: ...

        return generate_message()

async def format_conversation(messages: List[Message]) -> str:
    conversation = ""
    for message in messages:
        message_datetime_str = message.date_sent.strftime("%H:%M:%S")
        
        conversation += f"{message_datetime_str} {sender.value} says to {recipient.value}: {message}\n"
    

    
    return conversation



async def call_agent(messages: List[IncommingMessage], conversation: str) -> str:

    chat_agent = Agent(AI.ai_base_prompt)

    conversation = make_chat_log_entry(message, source, Recipient.KEEVA_ASSISTANT, conversation)

    while True:
        
        action: Action = await chat_agent.generate(conversation)
        conversation = make_chat_log_entry(action.message, Recipient.KEEVA_ASSISTANT, action.recipient, conversation)
        
        print(Recipient.KEEVA_ASSISTANT.value + ": " + action.message)

        if action.recipient == Recipient.HOME_ASSISTANT_AI_AGENT:
            message = await ask_home_assistant(action.message)
            conversation = make_chat_log_entry(message, Recipient.HOME_ASSISTANT_AI_AGENT, Recipient.KEEVA_ASSISTANT, conversation)

        if action.recipient == Recipient.USER:
            session: Session = [session for session in GLOBAL_STATE.sessions.values() if session.device.location == action.device][0]
            await session.websocket.send_text(action.message)
            return conversation

