from magentic import (
    prompt,
    OpenaiChatModel,
)
from pydantic import BaseModel, Field
from typing import Optional, List
from starlette.websockets import WebSocket
from dataclasses import dataclass
from .database import store_message, get_ai, AI as AI_Model, get_all_users_and_profiles, UserProfile, get_all_devices, DSN
from .data_models import Device, AI, AIMessage
from .state import MAIN_AI_QUEUE
from datetime import datetime
from .tools.home_assistant_tools import ask_home_assistant, TOOL_NAME as HOME_ASSISTANT_TOOL_NAME
import asyncio
import psycopg

@dataclass
class AssistantState:
    sessions: dict
    conversation: str
    ai_assistant: AI = None


@dataclass
class Session:
    device: Device
    websocket: WebSocket

# Agent related classes
class Action(BaseModel):
    message: str
    recipient: str = Field(
        description="The recipient of the action. keeva_assistant is yourself!",
    )
    device: Optional[str] = Field(
        description="The device to send the message to. (ONLY APPLIES TO USER RECIPIENTS)",
        default=None
    )

class AIAgent():
    def __init__(self, global_state: AssistantState = None): 
        self.global_state = global_state if global_state else AssistantState(sessions={}, conversation="")
        self.queue = MAIN_AI_QUEUE
        self.current_users = []
        self.all_devices = []
        self.updated_once = False

    async def _update_prompt(self):
        """
        Update the base prompt with the current conversation and connected devices.
        """
        # Fetch all users and profiles from the database
        async with await psycopg.AsyncConnection.connect(DSN) as conn:
            self.current_users: List[UserProfile] = await get_all_users_and_profiles(conn=conn)
            self.all_devices: List[Device] = await get_all_devices(conn=conn)
            self.ai_assistant: AI_Model = get_ai(1, conn=conn)
        
        registered_users = ", ".join([user.nick_name for user in self.current_users])
        connected_devices = ", ".join([session.device.location for session in self.global_state.sessions.values()])
        self.prompt = self.ai_assistant.ai_base_prompt + f"\nConnected devices are: {connected_devices}" + "\n" + f"Registered users: {registered_users}" + "\n" + "Conversation:" + "\n" + self.global_state.conversation


    async def _generate(self) -> List[Action]:

        @prompt(self.prompt)
        async def generate_message() -> List[Action]: ...

        return await generate_message()
    
    def add_session(self, device: Device, websocket: WebSocket):
        session = Session(device=device, websocket=websocket)
        self.global_state.sessions[device.unique_identifier] = session
        self.global_state.conversation = f"SYSTEM: Device {device.device_name} connected."
    
    # Updated make_chat_log_entry function
    def _make_chat_log_entry(
        message: str, 
        from_user: str, 
        to_user: str, 
        location: Optional[str] = None
    ) -> str:
        """
        Appends a new chat log entry in one of formats:
        
        With device info only:
        <timestamp> Device <from_device> (<from_user>): @<to_user> <message>
        
        With location only:
        <timestamp> <from_user> [<location>]: @<to_user> <message>
        
        Without device or location info:
        <timestamp> <from_user>: @<to_user> <message>
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Build the sender string based on available information
        if location:
            sender_str = f"{from_user} [{location}]"
        else:
            sender_str = f"{from_user}"
            
        return f"{timestamp} {sender_str}: @{to_user} {message}"
        
    
    async def _add_message(
        self, 
        message: str, 
        from_user: str, 
        to_user: str,  
        location: Optional[str] = None,
    ) -> None:
        """
        Add a message to the conversation and store it in the database.
        """
        formatted_message = self._make_chat_log_entry(
            message=message, 
            from_user=from_user, 
            to_user=to_user, 
            location=location
        )
        
        # Store the message in the database
        await store_message(
            message=formatted_message,
            date_sent=datetime.now(),
        )

        return formatted_message
    
    async def add_message(
        self,
        message: str,
        from_user: str,
        to_user: str,
        location: Optional[str] = None,
    ):
        await MAIN_AI_QUEUE.put(
            AIMessage(
                message=message,
                from_user=from_user,
                to_user=to_user,
                location=location,
            )
        )

    async def run(self):
        while True:
            incoming_message: AIMessage = await self.queue.get()
            
            message = await self._add_message(
                message=incoming_message.message,
                from_user=incoming_message.from_user,
                to_user=incoming_message.to_user,
                location=incoming_message.location,
            )

            # Add the message to conversation
            self.global_state.conversation += "\n" + message
            self.queue.task_done()

            # Update the prompt with the latest conversation and connected devices
            await self._update_prompt()

            # Process the message (e.g., send it to the AI model)

            actions: List[Action] = await self._generate()

            for action in actions:
                self.global_state.conversation += await self.add_message(
                    message=action.message,
                    from_user=AI.ai_name,
                    to_user=action.recipient,
                    put_in_queue=False
                )
                
                # Send the action message to the appropriate recipient
                if action.recipient == HOME_ASSISTANT_TOOL_NAME:
                    # Call Home Assistant Agent
                    asyncio.create_task(ask_home_assistant(action.message, caller=AI.ai_name))
                    
                elif action.recipient in [user for user in self.current_users if user.nick_name == action.recipient]:
                    # Find the right session based on device location
                    if action.device:
                        matching_sessions = [
                            session for session in self.global_state.sessions.values()
                            if session.device.location == action.device
                        ]
                        
                        if matching_sessions:
                            # Send message to the device
                            session = matching_sessions[0]
                            await session.websocket.send_text(action.message)
                        else:
                            # Log error if device not found
                            print(f"Error: Device '{action.device}' not found in sessions")
                            # Send to all connected devices as fallback
                            for session in self.global_state.sessions.sessions.values():
                                await session.websocket.send_text(action.message)
                    else:
                        # If no specific device mentioned, send to all
                        for session in self.global_state.sessions.sessions.values():
                            await session.websocket.send_text(action.message)
                
                else:
                    # For any other recipient that we don't handle, just log and return
                    print(f"Unhandled recipient: {action.recipient}")

    def start(self):
        asyncio.create_task(self.run())
        print("AI Agent started and running...")


# Initialize the AI agent with the base prompt and start it
AI_AGENT = AIAgent()