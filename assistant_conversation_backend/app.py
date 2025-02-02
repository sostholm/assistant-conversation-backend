# Create a starlette server

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute, Route
from starlette.websockets import WebSocket
from starlette.responses import JSONResponse
from .ai import call_agent
from .state import GLOBAL_STATE
from .data_models import IncommingMessage, AI as AI_model, Device, Recipient, Session
from .database import get_ai
from starlette.background import BackgroundTasks

from typing import List

async def assistant_event(request):
    data = await request.json()
    tasks = BackgroundTasks()
    tasks.add_task(call_agent, message=data['message'], source=Recipient.SYSTEM, conversation=GLOBAL_STATE.conversation)
    print(f"Received event: {data['message']}")
    return JSONResponse({"status": "ok"}, background=tasks)

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    device_info = await websocket.receive_json()

    # Convert the device_info dictionary to a Device object

    device = Device(**device_info)
    session = Session(device=device, websocket=websocket)
    # Create a new session
    GLOBAL_STATE.sessions[device.unique_identifier] = session

    conversation = ""
    try:
        async for messages in websocket.iter_json():
            messages: List[IncommingMessage]
            # Process the incoming message
            conversation = await call_agent(messages, conversation=conversation)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()


app = Starlette(
    routes=[
        Route("/event", endpoint=assistant_event, methods=["POST"]),
        WebSocketRoute('/ws', endpoint=websocket_endpoint),
    ]
)


