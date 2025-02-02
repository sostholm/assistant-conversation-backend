from starlette.websockets import WebSocket
from dataclasses import dataclass
from .data_models import Device, AI

@dataclass
class AssistantState:
    sessions: dict
    conversation: str
    ai_assistant: AI = None


@dataclass
class Session:
    device: Device
    websocket: WebSocket

GLOBAL_STATE = AssistantState(sessions={}, conversation="")