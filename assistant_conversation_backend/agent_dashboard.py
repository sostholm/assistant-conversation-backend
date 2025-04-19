from .agents.agent_crew import AgentCrew
from .tools.toolbox import Toolbox
from .data_models import Device, AI
from typing import Optional, List

def _get_dashboard(datetime, assistant_name, agent_crew: AgentCrew, toolbox: Toolbox, connected_devices: List[str], registered_users: List[str], task_board: str, home_assistant_dashboard: str) -> str:
    dashboard = f"""

**Context & Environment:**

* **Current date and time:** {datetime}
* **Current AI assistant (Your name):** {assistant_name}
{str(agent_crew)}
{str(toolbox)}
* **Connected devices are:** {connected_devices}
* **Registered users:** {registered_users}
{task_board}
* **Home Assistant Dashboard:**
{home_assistant_dashboard}
"""
    return dashboard