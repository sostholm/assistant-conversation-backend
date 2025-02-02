import asyncio
from typing import Callable
from .ai import call_agent, Recipient
from .state import GLOBAL_STATE, AssistantState

GLOBAL_STATE: AssistantState

async def running_task(identity: Recipient, function: Callable, timeout=30, *args, **kwargs):
    try:
        task = asyncio.create_task(function(*args, **kwargs))
        await asyncio.wait_for(task, timeout)
    except asyncio.TimeoutError:
        await call_agent("Task timed out.", identity, GLOBAL_STATE.conversation)
    except Exception as e:
        await call_agent(f"An error occurred: {e}", identity, GLOBAL_STATE.conversation)
