# Create a starlette server

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket
from .ai import call_agent

# from .ai import assistant_response

# Create a route to handle the POST request
# Create a function to handle the POST request
# Create a function to handle the GET request

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conversation = ""
    try:
        async for message in websocket.iter_text():
            # Process the incoming message
            conversation = await call_agent(message, conversation=conversation, websocket=websocket)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()


app = Starlette(
    routes=[
        # Route("/assistant", endpoint=assistant_response, methods=["POST"]),
        # Route("/assistant", endpoint=assistant_response, methods=["GET"]),
        WebSocketRoute('/ws', endpoint=websocket_endpoint),
    ]
)


