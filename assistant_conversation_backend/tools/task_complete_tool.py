from .base_tool import BaseTool
from .database_tools import complete_task
import inspect

class TaskCompleter(BaseTool):
    """
    Task completion tool for the assistant conversation.
    This class is responsible for marking tasks as completed.
    """

    async def complete(self, task_id: str):
        """
        Mark task complete by ID from 'Tasks' list. Example: /complete 01ABCDEF...
        :param task_id: The ID of the task to complete.
        """
        result = await complete_task(task_id)
        return result
        
    def __str__(self) -> str:
        """
        String representation of the TaskCompleter tool.
        Includes the tool description and available functions.
        """
        # Get class docstring
        description = self.__class__.__doc__.strip()
        
        # Get available functions (excluding special methods)
        methods = []
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if not name.startswith('_'):
                signature = str(inspect.signature(method))
                doc = method.__doc__.strip() if method.__doc__ else "No description"
                methods.append(f"- {name}{signature}: {doc}")
        
        functions_str = "\n".join(methods)
        
        return (
            f"Tool: {self.__class__.__name__}\n"
            f"Description: {description}\n\n"
            f"Available Functions:\n{functions_str}"
        )
