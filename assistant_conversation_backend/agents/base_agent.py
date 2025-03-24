class BaseAgent:

    @property
    def name(self) -> str:
        """Returns the name of the agent."""
        return self.__class__.__name__
    
    @property
    def description(self) -> str:
        """Returns the description of the agent."""
        return self.__doc__ or "No description available."
    
    @staticmethod
    async def ask(self, message: str, caller: str) -> str:
        """
        Sends a message to the agent and returns the response.
        
        Args:
            message (str): The message to send to the agent.
            caller (str): The caller of the agent.
        
        Returns:
            str: The response from the agent.
        """
        raise NotImplementedError("Subclasses must implement this method.")