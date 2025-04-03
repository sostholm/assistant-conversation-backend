from .base_tool import BaseTool
from ..state import MAIN_AI_QUEUE
from ..data_models import AIMessage
import inspect
import json
import os
from pathlib import Path

class ShortTermMemory(BaseTool):
    """
    Short-term memory for the assistant conversation.
    This class is responsible for storing and removing short-term memory data.
    Memories are indexed by numbers.
    Max memory size is 30.
    Max memory length is 10 words.
    """

    def __init__(self, storage_dir=None):
        """
        Initialize the short-term memory with file storage.
        :param storage_dir: Optional directory to store memory file.
                           If not specified, uses './data' directory within 
                           the application directory.
        """
        if storage_dir is None:
            # Use a default location in the application directory
            # This is more suitable for Docker environments
            storage_dir = Path('./data')
        
        self.storage_dir = Path(storage_dir)
        self.storage_file = self.storage_dir / "short_term_memory.json"
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Initialize the file if it doesn't exist
        if not self.storage_file.exists():
            self._save_to_file([])
        
        # Load initial memory from file
        self.memory = self._load_from_file()

    def _load_from_file(self):
        """
        Load memories from file.
        :return: List of memories.
        """
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            # Return empty list if file is empty or has invalid JSON
            return []

    def _save_to_file(self, memories):
        """
        Save memories to file.
        :param memories: List of memories to save.
        """
        with open(self.storage_file, 'w', encoding='utf-8') as file:
            json.dump(memories, file, ensure_ascii=False, indent=2)
    
    def remember(self, memory: str):
        """
        Add a memory to the short-term memory.
        :param memory: The memory to add.
        """
        # Load current memories
        memories = self._load_from_file()
        
        if len(memories) >= 30:
            raise MemoryError("Memory limit reached. Cannot add more memories.")
        
        memories.append(memory)
        self._save_to_file(memories)
        self.memory = memories  # Update in-memory copy
        
        return "Memory remembered"
    
    def forget(self, index: str):
        """
        Remove a memory from the short-term memory.
        :param memory: The memory to remove.
        """
        index = int(index)
        
        # Load current memories
        memories = self._load_from_file()
        
        if 0 <= index < len(memories):
            memories.pop(index)
            self._save_to_file(memories)
            self.memory = memories  # Update in-memory copy
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