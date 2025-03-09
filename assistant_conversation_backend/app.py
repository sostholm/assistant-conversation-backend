# Create a starlette server

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute, Route
from starlette.websockets import WebSocket
from starlette.responses import JSONResponse
from .data_models import IncomingMessage, AI as AI_model, Device, AIMessage
from starlette.background import BackgroundTasks
from .ai_agent import AI_AGENT
import asyncio

from typing import List

async def assistant_event(request):
    data = await request.json()

    # Validate the incoming data
    if 'message' not in data or 'nickname' not in data:
        return JSONResponse({"error": "Invalid data"}, status_code=400)

    add_message_arguments = {}
    add_message_arguments['message'] = data['message']
    add_message_arguments['from_user'] = data['nickname']
    add_message_arguments['to_user'] = data.get('to_user')
    add_message_arguments['location'] = data.get('location')

    asyncio.create_task(AI_AGENT.add_message(**add_message_arguments))
    print(f"Received event: {data['message']}")
    
    return JSONResponse({"status": "ok"})

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    device_info = await websocket.receive_json()

    # Convert the device_info dictionary to a Device object

    device = Device(**device_info)
    # Create a new session
    AI_AGENT.add_session(device, websocket)
    print(f"Device connected: {device.device_name}")

    try:
        async for messages in websocket.iter_json():
            messages: List[IncomingMessage]
            for msg in messages:
                # Convert the incoming message to an IncomingMessage object
                incoming_message = IncomingMessage(**msg)

                # Add the message to the AI agent's queue
                await AI_AGENT.add_message(
                    message=incoming_message.message,
                    from_user=incoming_message.nickname,
                    to_user="",
                    location=incoming_message.location,
                )
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()

def startup():
    # Start the AI agent
    AI_AGENT.start()
    print("AI agent started")

app = Starlette(
    routes=[
        Route("/event", endpoint=assistant_event, methods=["POST"]),
        WebSocketRoute('/ws', endpoint=websocket_endpoint),
    ],

    on_startup=[startup],
)


