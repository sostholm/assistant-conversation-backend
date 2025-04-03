class BaseTool:
    """Base class for all tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    async def parse_command(self, input):
        """Run the tool with the given arguments."""
        raise NotImplementedError("Subclasses must implement this method.")
    
    