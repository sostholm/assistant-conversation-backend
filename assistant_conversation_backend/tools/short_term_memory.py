from .base_tool import BaseTool
from ..state import MAIN_AI_QUEUE
from ..data_models import AIMessage
import inspect

class ShortTermMemory(BaseTool):
    """
    Short-term memory for the assistant conversation.
    This class is responsible for storing and removing short-term memory data.
    Memories are indexed by numbers.
    Max memory size is 30.
    Max memory length is 10 words.
    """

    def __init__(self):
        self.memory = []

    
    def remember(self, memory: str):
        """
        Add a memory to the short-term memory.
        :param memory: The memory to add.
        """
        if len(self.memory) >= 30:
            raise MemoryError("Memory limit reached. Cannot add more memories.")
        self.memory.append(memory)
        return "Memory remembered"
    
    def forget(self, index: str):
        """
        Remove a memory from the short-term memory.
        :param memory: The memory to remove.
        """
        index = int(index)

        if 0 <= index < len(self.memory):
            self.memory.pop(index)
        else:
            raise ValueError("Memory not found. Cannot remove non-existing memory.")

        return "Memory forgotten",

        
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