from pydantic import BaseModel, Field
from typing import List, Optional

# Agent related classes
class UserAction(BaseModel):
    message: str = Field(
        description="Message to the user or users. Do not include @<recipient> here"
    )
    recipient: str = Field(
        description="The recipient of the message.",
    )
    device: Optional[str] = Field(
        description="The device to send the message to.",
        default=None
    )

class AIAgentAction(BaseModel):
    message: str = Field(
        description="Message to the AI Agent.  Do not include @<recipient> here.",
        default=None
    )
    recipient: str = Field(
        description="The recipient of the message.",
    )

class ToolAction(BaseModel):
    command: str = Field(
        description="The tool command starting with '/' (e.g., '/search', '/calculate')",
    )
    arguments: str = Field(
        description="Space-separated arguments for the command",
        default=""
    )

class Actions(BaseModel):
    user_actions: List[UserAction] = Field(
        description="List of 1-3 messages to be sent to users.",
    )
    ai_agent_actions: List[AIAgentAction] = Field(
        description="List of 1-3 messages to be sent to other AI agents.",
    )
    tools_actions: List[ToolAction] = Field(
        description="List of actions to be performed by tools using slash commands.",
        default_factory=list
    )

class BaseAIModel:
    async def _generate(self, prompt_text) -> Actions:
        """
        Generate actions based on the model's capabilities.
        This method should be overridden by subclasses to provide specific implementations.
        """
        raise NotImplementedError("Subclasses must implement this method.")