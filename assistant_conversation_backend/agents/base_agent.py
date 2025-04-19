class BaseAgent:
    """Base class for all AI agents in the system."""
    
    @property
    def name(self) -> str:
        """
        Get the name of the agent.
        Default implementation returns the class name.
        """
        return self.__class__.__name__
    
    @property
    def description(self) -> str:
        """
        Get the description of the agent.
        Default implementation returns the class docstring.
        """
        return self.__doc__ or "No description available"
    
    async def ask(self, message: str, caller: str):
        """
        Send a message to this agent and get a response.
        Must be implemented by subclasses.
        
        Args:
            message: The message to send to the agent
            caller: The name of the entity sending the message
        """
        raise NotImplementedError("Subclasses must implement the ask method")