from .base_tool import BaseTool
from ..state import MAIN_AI_QUEUE
from ..data_models import AIMessage
import inspect
import asyncio
import sys
from ..database import get_ai_memories, update_ai_memories, DSN
import psycopg

# Fix for Windows event loop policy
if sys.platform.startswith('win'):
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

class ShortTermMemory(BaseTool):
    """
    Short-term memory for the assistant conversation.
    This class is responsible for storing and removing short-term memory data.
    Memories are indexed by numbers.
    Max memory size is 30.
    Max memory length is 10 words.
    
    Note: remember() and forget() methods are async and must be awaited.
    """

    def __init__(self, ai_id=1):
        """
        Initialize the short-term memory with database storage.
        :param ai_id: ID of the AI whose memories to manage (defaults to 1)
        """
        self.ai_id = ai_id
        # Initialize with empty memory that will be populated on first use
        self.memory = []
        
        # Run synchronous function to fetch initial memory
        self._init_memory()
    
    def _init_memory(self):
        """Initialize memory by running an async function in a sync context"""
        async def _async_init():
            async with await psycopg.AsyncConnection.connect(DSN) as conn:
                self.memory = await get_ai_memories(conn, self.ai_id)
        
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_async_init())
        finally:
            loop.close()
    
    async def remember(self, memory: str):
        """
        Add a memory to the short-term memory.
        :param memory: The memory to add.
        """
        if len(self.memory) >= 30:
            raise MemoryError("Memory limit reached. Cannot add more memories.")
        
        # Add memory locally
        self.memory.append(memory)
        
        # Update in database
        async with await psycopg.AsyncConnection.connect(DSN) as conn:
            await update_ai_memories(conn, self.ai_id, self.memory)
        
        return "Memory remembered"
    
    async def forget(self, index: str):
        """
        Remove a memory from the short-term memory.
        :param memory: The memory to remove.
        """
        index = int(index)
        
        if 0 <= index < len(self.memory):
            # Remove locally
            self.memory.pop(index)
            
            # Update in database
            async with await psycopg.AsyncConnection.connect(DSN) as conn:
                await update_ai_memories(conn, self.ai_id, self.memory)
        else:
            raise ValueError("Memory not found. Cannot remove non-existing memory.")

        return "Memory forgotten"
        
    def __str__(self) -> str:
        """
        String representation of the ShortTermMemory tool.
        Includes the tool description, available functions, and current memory content.
        """
        # Get class docstring
        description = self.__class__.__doc__.strip()
        
        # Get available functions (excluding special methods and get_memories)
        methods = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if not name.startswith('_') and name != 'get_memories':
                signature = str(inspect.signature(method))
                doc = method.__doc__.strip() if method.__doc__ else "No description"
                methods.append(f"- {name}{signature}: {doc}")
        
        functions_str = "\n".join(methods)
        
        # Get current memory content
        memory_content = "None" if not self.memory else "\n".join([f"{i}: {mem}" for i, mem in enumerate(self.memory)])
        
        return (
            f"Tool: {self.__class__.__name__}\n"
            f"Description: {description}\n\n"
            f"Available Functions:\n{functions_str}\n\n"
            f"Current Memory:\n{memory_content}"
        )