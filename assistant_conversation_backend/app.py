# Create a starlette server

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute, Route
from starlette.websockets import WebSocket
from starlette.responses import JSONResponse
from .data_models import IncomingMessage, AI as Device
from .ai_agent import AI_AGENT
import asyncio
import psycopg
from .database import DSN, get_device_by_id

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

    device_id = await websocket.receive_json()

    if isinstance(device_id, dict):
        device_id = device_id['id']
    
    device = None
    
    async with await psycopg.AsyncConnection.connect(DSN) as conn:
        device: Device = await get_device_by_id(conn, device_id)
        
        if device is None:
            await websocket.close(code=1008, reason="Device not found")
            return

    # Create a new session
    await AI_AGENT.add_session(device, websocket)
    print(f"Device connected: {device.device_name}")

    try:
        async for messages in websocket.iter_json():
            messages: List[IncomingMessage]
            for msg in messages:
                # Convert the incoming message to an IncomingMessage object
                try:
                    incoming_message = IncomingMessage(**msg)

                    # Add the message to the AI agent's queue
                    await AI_AGENT.add_message(
                        message=incoming_message.message,
                        from_user=incoming_message.nickname,
                        to_user="",
                        location=incoming_message.location,
                    )
                except TypeError as e:
                    print(f"Error converting message: {e}")
                    websocket.send_text(f"Error converting message: {e}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Remove the session when the connection is closed
        await AI_AGENT.remove_session(device)
        print(f"Device disconnected: {device.device_name}")
        try:
            await websocket.close()
        except Exception as e:
            print('Unable to close websocket. Probably already closed by client')

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


