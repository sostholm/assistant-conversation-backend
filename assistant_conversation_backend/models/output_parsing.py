import re
import shlex
from typing import List, Optional, Set
from pydantic import BaseModel, Field, ValidationError



output_instructions = """
**Output Format Instructions:**

Your entire response MUST be a multi-line text string following these rules:

1.  **Thought (Mandatory First Line):** Start the *first line* exactly with `Thought: ` followed by your internal reasoning or plan.
2.  **Actions (Subsequent Lines):** Each line after the `Thought:` line must represent ONE single action. Blank lines are ignored.
3.  **User Messages:** Use `@UserName ` (e.g., `@Sam `) followed by the message text.
4.  **Agent Messages:** Use `@AgentName ` (e.g., `@HomeAssistantAgent `) followed by the message text.
5.  **Tool Calls:** Use `/commandName ` followed by arguments. Arguments with spaces MUST be in double quotes (`"`). Examples:
    * `/remember "User meeting is at 3 PM"`
    * `/setLight living_room on 50%`
    * `/addTask "Call dentist" "Tomorrow 9:00 AM"`
6.  **One Action Per Line:** Do NOT put multiple `@` targets or `/` commands on the same line. Use a new line for each action.
7.  **No Action Needed:** If only internal thought is required, output *only* the `Thought:` line.
8.  **Ignored Lines:** Any line after `Thought:` that doesn't start with `@` or `/` will be ignored.
"""

# --- Pydantic Models (Ensure these match your definitions) ---

class UserAction(BaseModel):
    message: str = Field(
        description="Message to the user or users. Do not include @<recipient> here"
    )
    recipient: str = Field(
        description="The recipient of the message.",
    )
    # NOTE: 'device' and 'location' are NOT populated by this parser from '@User'
    # Delivery logic needs external context (e.g., original message location)
    # Add them back if your delivery logic requires them *within* this model
    # device: Optional[str] = Field(default=None)
    # location: Optional[str] = Field(default=None)


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
        description="The tool command (e.g., 'remember', 'complete')",
    )
    # Store the raw arguments string as received after the command
    arguments: str = Field(
        description="Raw arguments string following the command.",
        default=""
    )


class Actions(BaseModel):
    thought: Optional[str] = Field(
        description="The AI's reasoning, internal thoughts, or plan.",
        default=None
    )
    user_actions: List[UserAction] = Field(
        description="List of messages to be sent to users.",
        default_factory=list # Ensure default is an empty list
    )
    ai_agent_actions: List[AIAgentAction] = Field(
        description="List of messages to be sent to other AI agents.",
        default_factory=list # Ensure default is an empty list
    )
    tools_actions: List[ToolAction] = Field(
        description="List of actions to be performed by tools.",
        default_factory=list # Ensure default is an empty list
    )


class ParsingError(ValueError):
    """Custom exception for parsing errors in LLM output."""
    pass

# --- Parsing Function ---

def parse_llm_output_to_actions(
    llm_output: str,
    known_agent_names: Set[str]
) -> Actions:
    """
    Parses the multi-line text output from the LLM into structured Actions.

    Args:
        llm_output: The raw string output from the LLM.
        known_agent_names: A set of strings containing the names of known AI agents
                           to differentiate them from user recipients.

    Returns:
        An Actions Pydantic model instance.

    Raises:
        ParsingError: If the input format is invalid (e.g., missing Thought).
    """
    lines = llm_output.strip().split('\n')
    if not lines:
        raise ParsingError("LLM output is empty.")

    # 1. Parse Thought
    first_line = lines[0].strip()
    if not first_line.startswith("Thought: "):
        raise ParsingError("LLM output must start with 'Thought: '.")
    thought = first_line[len("Thought: "):].strip()
    if not thought:
        # Allow empty thoughts, but maybe log a warning if desired
        pass # Or raise ParsingError("Thought content is missing.")

    # Initialize action lists
    user_actions: List[UserAction] = []
    ai_agent_actions: List[AIAgentAction] = []
    tools_actions: List[ToolAction] = []

    # Regex patterns
    # Matches @Recipient Message (Captures Recipient and Message)
    mention_pattern = re.compile(r"^@(\w+)\s+(.*)$")
    # Matches /command arguments (Captures command and arguments string)
    tool_pattern = re.compile(r"^/(\w+)\s*(.*)$") # Capture command and the rest

    # 2. Parse Actions (lines after Thought)
    for line in lines[1:]:
        line = line.strip()
        if not line:  # Skip empty lines
            continue

        mention_match = mention_pattern.match(line)
        tool_match = tool_pattern.match(line)

        if mention_match:
            recipient = mention_match.group(1)
            message = mention_match.group(2).strip()
            if not message:
                 print(f"Warning: Ignoring empty message for recipient @{recipient}")
                 continue # Or raise ParsingError

            if recipient in known_agent_names:
                ai_agent_actions.append(AIAgentAction(recipient=recipient, message=message))
            else:
                # Assume it's a user if not a known agent
                user_actions.append(UserAction(recipient=recipient, message=message))

        elif tool_match:
            command = tool_match.group(1)
            arguments_str = tool_match.group(2).strip() # Get the raw arguments string
            if not command:
                 print(f"Warning: Ignoring tool call with empty command: {line}")
                 continue # Or raise ParsingError

            tools_actions.append(ToolAction(command=command, arguments=arguments_str))

        else:
            # Handle lines that don't match expected patterns
            # Option 1: Strict - Raise Error
            # raise ParsingError(f"Invalid line format: '{line}'")
            # Option 2: Lenient - Log Warning and Ignore
             print(f"Warning: Ignoring line with unrecognized format: '{line}'")

    # 3. Construct Actions object
    try:
        actions_obj = Actions(
            thought=thought,
            user_actions=user_actions,
            ai_agent_actions=ai_agent_actions,
            tools_actions=tools_actions
        )
        return actions_obj
    except ValidationError as e:
        # This might catch issues if default_factory wasn't used correctly
        # or if future Pydantic validation is added.
        raise ParsingError(f"Failed to validate parsed actions: {e}")


# --- Example Usage & Basic Tests ---

if __name__ == "__main__":
    known_agents = {"HomeAssistantAgent", "WebSearchAgent"}

    # Test Case 1: Simple user message
    output1 = """Thought: User asked for the time. I should tell them.
@Sam The current time is 10:15 AM.
"""
    try:
        actions1 = parse_llm_output_to_actions(output1, known_agents)
        print("Test Case 1 PASSED:")
        print(actions1.model_dump_json(indent=2))
        assert actions1.thought == "User asked for the time. I should tell them."
        assert len(actions1.user_actions) == 1
        assert actions1.user_actions[0].recipient == "Sam"
        assert actions1.user_actions[0].message == "The current time is 10:15 AM."
        assert not actions1.ai_agent_actions
        assert not actions1.tools_actions
    except ParsingError as e:
        print(f"Test Case 1 FAILED: {e}")

    print("-" * 20)

    # Test Case 2: Multiple actions (User, Agent, Tool)
    output2 = """Thought: User Alex wants the living room light dimmed and asked about the weather. I'll ask HA to dim the light, ask WebSearch for weather, and remind myself to follow up.
@HomeAssistantAgent Set entity light.living_room_main brightness_pct 40
@WebSearchAgent What is the weather forecast for Katowice today?
/remember "Alex asked for weather and living room dimming"
@Alex Okay, I'll dim the living room light and check the weather for you!
"""
    try:
        actions2 = parse_llm_output_to_actions(output2, known_agents)
        print("Test Case 2 PASSED:")
        print(actions2.model_dump_json(indent=2))
        assert actions2.thought is not None
        assert len(actions2.user_actions) == 1
        assert actions2.user_actions[0].recipient == "Alex"
        assert len(actions2.ai_agent_actions) == 2
        assert actions2.ai_agent_actions[0].recipient == "HomeAssistantAgent"
        assert actions2.ai_agent_actions[1].recipient == "WebSearchAgent"
        assert len(actions2.tools_actions) == 1
        assert actions2.tools_actions[0].command == "remember"
        assert actions2.tools_actions[0].arguments == '"Alex asked for weather and living room dimming"' # Note: preserves quotes if LLM includes them, otherwise not. shlex handles parsing later if needed by tool.
    except ParsingError as e:
        print(f"Test Case 2 FAILED: {e}")

    print("-" * 20)

     # Test Case 3: Tool with complex arguments (needs shlex in tool handler)
    output3 = """Thought: User wants to set a complex light scene.
/setLight "living room lamp" on 75% "blue" effect=pulse
"""
    try:
        actions3 = parse_llm_output_to_actions(output3, known_agents)
        print("Test Case 3 PASSED:")
        print(actions3.model_dump_json(indent=2))
        assert len(actions3.tools_actions) == 1
        assert actions3.tools_actions[0].command == "setLight"
        assert actions3.tools_actions[0].arguments == '"living room lamp" on 75% "blue" effect=pulse'
        # Example of how the tool handler might parse arguments:
        tool_args = shlex.split(actions3.tools_actions[0].arguments, posix=True)
        print(f"Tool handler would parse arguments as: {tool_args}")
        assert tool_args == ['living room lamp', 'on', '75%', 'blue', 'effect=pulse']
    except ParsingError as e:
        print(f"Test Case 3 FAILED: {e}")

    print("-" * 20)


    # Test Case 4: Only thought
    output4 = "Thought: System event processed, no user action needed."
    try:
        actions4 = parse_llm_output_to_actions(output4, known_agents)
        print("Test Case 4 PASSED:")
        print(actions4.model_dump_json(indent=2))
        assert actions4.thought == "System event processed, no user action needed."
        assert not actions4.user_actions
        assert not actions4.ai_agent_actions
        assert not actions4.tools_actions
    except ParsingError as e:
        print(f"Test Case 4 FAILED: {e}")

    print("-" * 20)

    # Test Case 5: Missing Thought (Error)
    output5 = "@Sam Hello there!"
    try:
        actions5 = parse_llm_output_to_actions(output5, known_agents)
        print(f"Test Case 5 FAILED (Expected Error): Parsed {actions5}")
    except ParsingError as e:
        print(f"Test Case 5 PASSED (Caught Error): {e}")

    print("-" * 20)

    # Test Case 6: Invalid line format (Warning/Ignore)
    output6 = """Thought: User message was unclear.
This line is invalid.
@Sam Can you please clarify what you meant?
/remember "User message unclear at HH:MM"
"""
    try:
        print("Test Case 6 (Warning/Ignore):")
        actions6 = parse_llm_output_to_actions(output6, known_agents)
        print(actions6.model_dump_json(indent=2))
        # Should parse successfully but print a warning for the invalid line
        assert len(actions6.user_actions) == 1
        assert len(actions6.tools_actions) == 1
    except ParsingError as e:
        print(f"Test Case 6 FAILED: {e}")