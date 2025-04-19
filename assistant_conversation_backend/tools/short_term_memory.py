from .base_tool import BaseTool
import inspect
from typing import List, Dict, Optional, Union

class ShortTermMemory(BaseTool):
    """
    Stores and removes short-term memories (indexed, max 30, max 10 words each).
    """
    
    def __init__(self):
        """
        Initialize the short-term memory tool with an empty memory store.
        """
        self.memories: Dict[int, str] = {}
        self.max_memories = 30
    
    def remember(self, memory: str) -> str:
        """
        Adds memory to short-term memory. Example: /remember "Meeting at 3"
        :param memory: The memory text to store.
        """
        # Find the next available index
        index = 0
        while index in self.memories and index < self.max_memories:
            index += 1
            
        if index >= self.max_memories:
            # Memory is full, replace the first item
            min_index = min(self.memories.keys()) if self.memories else 0
            self.memories[min_index] = memory
            return f"Memory updated at index {min_index}: '{memory}'"
            
        # Store the new memory
        self.memories[index] = memory
        return f"Memory added at index {index}: '{memory}'"
    
    def forget(self, index: Union[str, int]) -> str:
        """
        Removes memory by index. Example: /forget 1
        :param index: The index of the memory to remove.
        """
        try:
            index = int(index)
            if index in self.memories:
                memory = self.memories.pop(index)
                return f"Removed memory {index}: '{memory}'"
            else:
                return f"No memory found at index {index}"
        except ValueError:
            return f"Invalid index: {index}. Please provide a number."
    
    def list_memories(self) -> str:
        """
        Lists all memories currently stored. Example: /list_memories
        """
        if not self.memories:
            return "No memories stored."
            
        result = []
        for idx, memory in sorted(self.memories.items()):
            result.append(f"{idx}: {memory}")
            
        return "\n".join(result)
    
    def __str__(self) -> str:
        """
        String representation of the ShortTermMemory tool.
        Includes the tool description, available functions, and current memories.
        """
        # Get class docstring
        description = self.__class__.__doc__.strip()
        
        # Get available functions (excluding special methods)
        methods = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if not name.startswith('_'):
                signature = str(inspect.signature(method))
                doc = method.__doc__.strip() if method.__doc__ else "No description"
                methods.append(f"        * `{name}{signature}`: {doc}")
        
        functions_str = "\n".join(methods)
        
        # Format current memories
        memory_lines = []
        for idx, memory in sorted(self.memories.items()):
            memory_lines.append(f"        {idx}: {memory}")
        
        memories_str = "\n".join(memory_lines) if memory_lines else "        (No memories stored)"
        
        return (
            f"    * Description: {description}\n"
            f"    * Available Functions:\n{functions_str}\n"
            f"    * **Current Memory:**\n{memories_str}"
        )