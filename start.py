from assistant_conversation_backend.app import app
import asyncio

# Check if the platform is Windows and set the event loop policy
import sys
if sys.platform.startswith("win"):
    from asyncio import WindowsSelectorEventLoopPolicy

    # Set the event loop policy to WindowsSelectorEventLoopPolicy
    # This is necessary for compatibility with Windows
    # when using asyncio and uvicorn
    if sys.version_info >= (3, 8):
        # For Python 3.8 and above
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())


# Run the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)