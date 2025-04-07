class BaseTool:
    """Base class for all tools."""

    async def parse_command(self, input):
        """Run the tool with the given arguments."""
        raise NotImplementedError("Subclasses must implement this method.")
    
    