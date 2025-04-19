from typing import List
from .base_tool import BaseTool


class Toolbox:
    """
    A container for tools that provides a structured way to access and display them.
    """
    
    def __init__(self, tools: List[BaseTool] = None):
        """
        Initialize the toolbox with optional initial tools.
        
        :param tools: Optional list of tools to add to the toolbox
        """
        self.tools = tools or []
        
    def register_tool(self, tool: BaseTool) -> None:
        """
        Add a tool to the toolbox.
        
        :param tool: The tool to add
        """
        if tool not in self.tools:
            self.tools.append(tool)
            
    def register_tools(self, tools: List[BaseTool]) -> None:
        """
        Add multiple tools to the toolbox.
        
        :param tools: List of tools to add
        """
        for tool in tools:
            self.register_tool(tool)
            
    def get_tool_by_name(self, name: str) -> BaseTool:
        """
        Get a tool by its class name.
        
        :param name: The class name of the tool
        :return: The tool instance or None if not found
        """
        for tool in self.tools:
            if tool.__class__.__name__ == name:
                return tool
        return None
    
    def __str__(self) -> str:
        """
        Format all tools in a structured way.
        
        The format follows:
        * **Tool: ToolName**
            * Description: Tool description
            * Available Functions:
                * `function_name(params)`: Function description
        """
        if not self.tools:
            return "No tools registered."
            
        output = ["## Tools Available"]
        
        for tool in self.tools:
            # Use the tool's own __str__ method which formats it according to requirements
            output.append(f"* **Tool: {tool.__class__.__name__}**\n{str(tool)}")
            
        return "\n".join(output)
