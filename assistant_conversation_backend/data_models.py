from dataclasses import dataclass
from starlette.websockets import WebSocket
from datetime import datetime
from enum import Enum

@dataclass
class Device:
    id: int
    device_name: str
    device_type_id: int
    unique_identifier: str
    ip_address: str
    mac_address: str
    location: str
    status: str
    created_at: datetime
    updated_at: datetime

@dataclass
class AI:
    ai_id: int
    ai_name: str
    ai_base_prompt: str


@dataclass
class Message:
    message_id: int
    conversation_id: str
    from_user: str
    to_user: str
    from_device_id: int = None
    date_sent: datetime
    content: str

@dataclass
class IncommingMessage:
    nickname: str
    message: str
    location: str

@dataclass
class AssistantState:
    sessions: dict
    conversation: str
    ai_assistant: AI = None


@dataclass
class Session:
    device: Device
    websocket: WebSocket

class Recipient(Enum):
    USER = "user"
    KEEVA_ASSISTANT = "keeva-assistant"
    HOME_ASSISTANT_AI_AGENT = "home_assistant_ai_agent"
    SYSTEM = "system"
