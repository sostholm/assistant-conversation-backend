from typing import Optional, List
from starlette.websockets import WebSocket
from dataclasses import dataclass
from .database import store_message, get_ai, AI as AI_Model, get_all_users_and_profiles, UserProfile, get_all_devices, DSN, get_last_n_messages, Message, get_tasks_for_execution, Task
from .data_models import Device, AI, AIMessage
from .state import MAIN_AI_QUEUE
from .models.base_model import Actions, ToolAction
from datetime import datetime
from .agents.home_assistant_agent import HomeAssistantAgent
from .agents.web_search_agent import WebSearchAgent
from .misc_functions import get_dashboard_summary
from .models.open_ai_4o import OpenAI4o
from .tools.short_term_memory import ShortTermMemory
from .tools.task_complete_tool import  TaskCompleter
import asyncio
import psycopg


llm_model = OpenAI4o()

home_assistant_agent = HomeAssistantAgent()
web_search_agent = WebSearchAgent()

short_term_memory = ShortTermMemory()
task_completer = TaskCompleter()

toolbox = [short_term_memory, task_completer]

example_conversations = """
Here is an example conversation, remember the user can't see what Agents say!:
User [living_room]: Hello, how are you?
AI: @User I'm doing well, thank you! How can I assist you today?
User [living_room]: Can you tell me the weather today?
AI: @WebSearchAgent Can you find the weather for today?
WebSearchAgent: @AI Sure! The weather today is sunny with a high of 75°F.
AI: @User The weather today is sunny with a high of 75°F.
User [living_room]: Can you turn on the living room lights?
AI: @HomeAssistantAgent Can you turn on the living room lights?
HomeAssistantAgent: @AI Sure! Turning on the living room lights now.
AI: @User The living room lights are now on.
User [living_room]: Can you set a reminder for my meeting tomorrow at 10 AM?
AI: @DataBaseAgent Can you set a reminder for User's meeting tomorrow at 10 AM?
DataBaseAgent: @AI Sure! Reminder set for User's meeting tomorrow at 10 AM.
AI: @User Reminder set for your meeting tomorrow at 10 AM.
User [living_room]: Can you play some music?
AI: @HomeAssistantAgent Could you play some music on the living room speaker?
HomeAssistantAgent: @AI Playing music now
AI: @User Playing some music now.
"""

@dataclass
class AssistantState:
    sessions: dict
    conversation: str
    ai_assistant: AI = None


@dataclass
class Session:
    device: Device
    websocket: WebSocket


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
            messages: Message = await get_last_n_messages(conn=conn, n=30)
            tasks: Task = await get_tasks_for_execution(conn=conn)

        home_assistant_dashboard = await get_dashboard_summary()

        # Format the task board with times in "3:30 PM" format
        task_board = "\n".join([
            f"Task {task.task_id}: {task.task_description} - Due: {task.task_execute_at.strftime('%I:%M %p on %A, %b %d')}" 
            for task in tasks
        ])
        
        registered_users = ", ".join([user.nick_name for user in self.current_users])
        connected_devices = ", ".join([session.device.location for session in self.global_state.sessions.values()])
        self.prompt = self.ai_assistant.ai_base_prompt + "\n"
        self.prompt += f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + "\n"
        self.prompt += f"Current AI assistant (Your name): {self.ai_assistant.ai_name}" + "\n"
        self.prompt += f"AI Agents: {', '.join([home_assistant_agent.name + ': ' + home_assistant_agent.description, web_search_agent.name + ': ' + web_search_agent.description])}" + "\n"
        self.prompt += "To talk to AI Agents, do @<ai_agent_name>" + "\n"
        self.prompt += str(short_term_memory) + "\n"
        self.prompt += str(task_completer) + "\n"
        self.prompt += example_conversations + "\n"
        self.prompt += f"Connected devices are: {connected_devices}" + "\n" 
        self.prompt += f"Registered users: {registered_users}" + "\n"
        self.prompt += f"Tasks for the next 24 hours: {task_board}" + "\n"
        self.prompt += "home assistant dashboard: " + home_assistant_dashboard + "\n"
        self.prompt += "YOU'RE NOT ALWAYS REQUIRED TO RESPOND, IT MAY HAPPEN THAT THE APPROPRIATE ACTION IS TO NOT RESPOND" + "\n"
        self.prompt += "THE USERS CAN'T SEE THE CHAT, ONLY MESSAGES @THEM. YOU HAVE TO TALK TO THEM THROUGH THE CONNECTED DEVICES." + "\n"
        self.prompt += "You can do 1-3 actions at one time!"
        self.prompt += "DON'T DO rogue actions: executing multiple actions in a single turn without waiting for environmental feedback, assuming success based on internal simulation" + "\n"
        self.prompt += "Conversation latest 30 messages:" + "\n".join([message.content for message in reversed(messages)])

    
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

            try:
                actions: Actions = await llm_model._generate(self.prompt)
            except Exception as e:
                print(f"Error generating message: {e}")
                await self.add_message(
                    message=f"Error generating message: {e} \n sleeping loop for 10 seconds",
                    from_user="SYSTEM",
                    to_user='',
                    location='SYSTEM',
                )
                await asyncio.sleep(10)
                continue

            for action in actions.ai_agent_actions:
                if action.message is None:
                    continue
                
                await self._add_message(
                    message=action.message,
                    from_user=self.ai_assistant.ai_name,
                    to_user=action.recipient,
                    location="",
                )

                # Send the action message to the appropriate recipient
                # Check normal and camel case turned to spaces
                if action.recipient == home_assistant_agent.name or action.recipient == "Home Assistant Agent":
                    # Call Home Assistant Agent
                    asyncio.create_task(home_assistant_agent.ask(action.message, caller=self.ai_assistant.ai_name))
                
                elif action.recipient == web_search_agent.name or action.recipient == "Web Search Agent":
                    asyncio.create_task(web_search_agent.ask(action.message, caller=self.ai_assistant.ai_name))

            for action in actions.user_actions:
                if action.message is None:
                    continue

                await self._add_message(
                    message=action.message,
                    from_user=self.ai_assistant.ai_name,
                    to_user=action.recipient,
                    location="",
                )

                if action.recipient in [user.nick_name for user in self.current_users if user.nick_name == action.recipient]:
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
                                error_text = f"Error: Device '{action.device}' not found in sessions"
                                print(error_text)
                                await self.add_message(
                                    message=error_text,
                                    from_user="SYSTEM",
                                    to_user='',
                                    location='SYSTEM',
                                )
                        
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
                    print(f"Unhandled recipient: {action.recipient}")
                    await self.add_message(
                        message=f"Error: Unhandled recipient '{action.recipient}'",
                        from_user="SYSTEM",
                        to_user='',
                        location='SYSTEM',
                    )

            for tool_call in actions.tools_actions:
                tool_call: ToolAction

                await self.add_message(
                    message=f"Tool call: {tool_call.command} with arguments: {tool_call.arguments}",
                    from_user=self.ai_assistant.ai_name,
                    to_user='',
                    location='',
                )

                handled = False
                for tool in toolbox:
                    if hasattr(tool, tool_call.command):
                        try:
                            # Get the function corresponding to the command
                            func = getattr(tool, tool_call.command)
                            # Call the function with the parameters, handling async functions
                            if asyncio.iscoroutinefunction(func):
                                result = await func(tool_call.arguments)
                            else:
                                result = func(tool_call.arguments)
                            
                            # Log the result
                            await self.add_message(
                                message=f"Tool {tool.__class__.__name__} executed command '{tool_call.command}' with result: {result}",
                                from_user="SYSTEM",
                                to_user=self.ai_assistant.ai_name,  # Send result back to AI
                                location='SYSTEM',
                            )
                            handled = True
                            break
                        except Exception as e:
                            # Log error if tool execution fails
                            error_text = f"Error executing tool command '{tool_call.command}': {e}"
                            print(error_text)
                            await self.add_message(
                                message=error_text,
                                from_user="SYSTEM",
                                to_user='',
                                location='SYSTEM',
                            )
                
                if not handled:
                    # Log error if no tool can handle the command
                    error_text = f"No tool found to handle command '{tool_call.command}'"
                    print(error_text)
                    await self.add_message(
                        message=error_text,
                        from_user="SYSTEM",
                        to_user='',
                        location='SYSTEM',
                    )

    def start(self):
        asyncio.create_task(self.run())
        print("AI Agent started and running...")

# Initialize the AI agent with the base prompt and start it
AI_AGENT = AIAgent()