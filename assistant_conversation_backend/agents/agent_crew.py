from typing import Dict, List, Optional, Type
from .base_agent import BaseAgent
from .home_assistant_agent import HomeAssistantAgent
from .web_search_agent import WebSearchAgent

class AgentCrew:
    """A registry for all AI agents available in the system."""
    
    def __init__(self, agents: Optional[List[BaseAgent]] = None):
        """
        Initialize the AgentCrew.

        Args:
            agents: An optional list of agents to register initially. 
                    If None, default agents (HomeAssistantAgent, WebSearchAgent) will be registered.
        """
        self.agents: Dict[str, BaseAgent] = {}
        if agents is not None:
            for agent in agents:
                self.register_agent(agent)
        else:
            # Register default agents if none are provided
            self.register_agent(HomeAssistantAgent())
            self.register_agent(WebSearchAgent())
    
    def register_agent(self, agent: BaseAgent):
        """Register a new agent with the crew."""
        if not isinstance(agent, BaseAgent):
            raise TypeError("Only instances of BaseAgent can be registered.")
        self.agents[agent.name] = agent
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self.agents.get(name)
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all registered agents."""
        return list(self.agents.values())
    
    def get_agent_names(self) -> List[str]:
        """Get names of all registered agents."""
        return list(self.agents.keys())
    
    def __str__(self) -> str:
        """
        Format the available agents as a markdown string for display.
        
        Returns:
            A markdown formatted string describing all available agents.
        """
        if not self.agents:
            return "* **AI Agents:** None available"
        
        markdown = "* **AI Agents:**\n"
        for agent in self.agents.values():
            # Extract the first sentence of the docstring as a short description
            description = agent.__doc__.strip().split('.')[0] if agent.__doc__ else "No description available"
            markdown += f"    * `{agent.name}`: {description}.\n"
        
        markdown += "    * To talk to AI Agents, use `@<ai_agent_name>`"
        
        return markdown
    
    def to_markdown(self) -> str:
        """
        Format the available agents as a markdown string for display.
        
        Returns:
            A markdown formatted string describing all available agents.
            
        Note:
            This method is deprecated. Please use str(agent_crew) instead.
        """
        return str(self)
