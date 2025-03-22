from magentic import (
    prompt,
    OpenaiChatModel,
)
from pydantic import BaseModel, Field
from typing import Optional, List
from starlette.websockets import WebSocket
from dataclasses import dataclass
from .database import store_message, get_ai, AI as AI_Model, get_all_users_and_profiles, UserProfile, get_all_devices, DSN, get_last_n_messages, Message, get_tasks_for_next_24_hours, Task
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
    message: str = None
    recipient: str = Field(
        description="The recipient of the action.",
        default=None
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
            self.ai_assistant: AI_Model = await get_ai(1, conn=conn)
            messages: Message = await get_last_n_messages(conn=conn, n=20)
            tasks: Task = await get_tasks_for_next_24_hours(conn=conn)

        task_board = "\n".join([f"Task: {task.short_description} - Due: {task.due_date}" for task in tasks])
        
        registered_users = ", ".join([user.nick_name for user in self.current_users])
        connected_devices = ", ".join([session.device.location for session in self.global_state.sessions.values()])
        self.prompt = self.ai_assistant.ai_base_prompt + "\n"
        self.prompt += f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + "\n"
        self.prompt += f"Current AI assistant (Your name): {self.ai_assistant.ai_name}" + "\n"
        self.prompt += f"Connected devices are: {connected_devices}" + "\n" 
        self.prompt += f"Registered users: {registered_users}" + "\n"
        self.prompt += f"Tasks for the next 24 hours: {task_board}" + "\n"
        self.prompt += "YOU'RE NOT ALWAYS REQUIRED TO RESPOND, IT MAY HAPPEN THAT THE APPROPRIATE ACTION IS TO NOT RESPOND" + "\n"
        self.prompt += "Conversation:" + "\n".join([message.content for message in messages])


    async def _generate(self) -> List[Action]:

        @prompt(self.prompt)
        async def generate_message() -> List[Action]: ...

        return await generate_message()
    
    async def add_session(self, device: Device, websocket: WebSocket):
        session = Session(device=device, websocket=websocket)
        self.global_state.sessions[device.location] = session
        await self.add_message(f"Device {device.device_name} connected.", from_user="SYSTEM", to_user='', location=device.location)
    
    async def remove_session(self, device: Device):
        if device.location in self.global_state.sessions:
            del self.global_state.sessions[device.location]
            await self.add_message(f"Device {device.device_name} disconnected.", from_user="SYSTEM", to_user='', location=device.location)
        else:
            print(f"Error: Device {device.device_name} not found in sessions.")
    
    # Updated make_chat_log_entry function
    def _make_chat_log_entry(
        self,
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
        
        if to_user:
            receiver_str = f"@{to_user}"
        else:
            receiver_str = ""
        
        return f"{timestamp} {sender_str}: {receiver_str} {message}"
        
    
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
            message, 
            from_user, 
            to_user, 
            location
        )
        
        # Store the message in the database
        await store_message(
            message=formatted_message,
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

            try:
                actions: List[Action] = await self._generate()
            except Exception as e:
                print(f"Error generating message: {e}")
                await self.add_message(
                    message=f"Error generating message: {e} \n sleeping loop for 10 seconds",
                    from_user="SYSTEM",
                    to_user='',
                    location='SYSTEM',
                )
                asyncio.sleep(10)
                continue

            for action in actions:
                if action.message is None:
                    # Skip empty actions
                    continue

                self.global_state.conversation += self._make_chat_log_entry(
                    message=action.message,
                    from_user=self.ai_assistant.ai_name,
                    to_user=action.recipient,
                )
                
                # Send the action message to the appropriate recipient
                if action.recipient == HOME_ASSISTANT_TOOL_NAME:
                    # Call Home Assistant Agent
                    asyncio.create_task(ask_home_assistant(action.message, caller=AI.ai_name))
                    
                elif action.recipient in [user.nick_name for user in self.current_users if user.nick_name == action.recipient]:
                    try:
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
                            for session in self.global_state.sessions.values():
                                await session.websocket.send_text(action.message)
                    except Exception as e:
                        print(f"Error sending message to device: {e}")
                        await self.add_message(
                            message=f"Error sending message to device: {e}",
                            from_user="SYSTEM",
                            to_user='',
                            location='SYSTEM',
                        )
                else:
                    # For any other recipient that we don't handle, just log and return
                    print(f"Unhandled recipient: {action.recipient}")
                    await self.add_message(
                        message=f"Error: Unhandled recipient '{action.recipient}'",
                        from_user="SYSTEM",
                        to_user='',
                        location='SYSTEM',
                    )

    def start(self):
        asyncio.create_task(self.run())
        print("AI Agent started and running...")


# Initialize the AI agent with the base prompt and start it
AI_AGENT = AIAgent()