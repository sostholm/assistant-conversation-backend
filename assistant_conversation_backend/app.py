# Create a starlette server

from starlette.applications import Starlette
from starlette.routing import Route

from .ai import assistant_response

# Create a route to handle the POST request
# Create a function to handle the POST request
# Create a function to handle the GET request


app = Starlette(
    routes=[
        Route("/assistant", endpoint=assistant_response, methods=["POST"]),
        Route("/assistant", endpoint=assistant_response, methods=["GET"]),
    ]
)


