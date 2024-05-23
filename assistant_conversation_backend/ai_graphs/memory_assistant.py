from langgraph.prebuilt import ToolExecutor
from langchain_openai import ChatOpenAI
from langchain.tools.render import format_tool_to_openai_function
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.prebuilt import ToolInvocation
import json
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, END
from ..tools.database_tools import create_task, update_task, create_event, add_shopping_item, get_events, get_tasks, get_shopping_list
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool, StructuredTool, tool
from .ai_models import get_tools_model
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

tools = [create_task, update_task, create_event, add_shopping_item, get_events, get_tasks, get_shopping_list]
tool_executor = ToolExecutor(tools)

model = get_tools_model()

functions = [format_tool_to_openai_function(t) for t in tools]
model = model.bind_tools(functions)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

def get_base_prompt():


    return (
        "You are a memory assistant. You're responsible for manageing the memory of the assistant."
        "You're part of a team of other assistants, each with their own responsibilities."
        "You will provide information about the memory of the assistant and answer questions using the information provided."
        "You can also change the memory of the assistant"
        "The memory is stored in a postgres database."
        "Here is a list of tables currently in the database: user_profile, tasks, events, shopping_list, conversations, messages"
        "conversations and messages are stored automatically by the assistant."
    )

# Define the function that determines whether to continue or not
def should_continue(state):
    last_message = state["messages"][-1]
    # If there are no tool calls, then we finish
    if "tool_calls" not in last_message.additional_kwargs:
        return "end"
    # If there is a Response tool call, then we finish
    elif any(
        tool_call["function"]["name"] == "Response"
        for tool_call in last_message.additional_kwargs["tool_calls"]
    ):
        return "end"
    # Otherwise, we continue
    else:
        return "continue"

# Define the function that calls the model
def call_model(state):
    messages = state['messages']
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}

# Define the function to execute tools
def call_tool(state):
    messages = state["messages"]
    # We know the last message involves at least one tool call
    last_message = messages[-1]

    # We loop through all tool calls and append the message to our message log
    for tool_call in last_message.additional_kwargs["tool_calls"]:
        action = ToolInvocation(
            tool=tool_call["function"]["name"],
            tool_input=json.loads(tool_call["function"]["arguments"]),
            id=tool_call["id"],
        )

        # We call the tool_executor and get back a response
        response = tool_executor.invoke(action)
        # We use the response to create a FunctionMessage
        function_message = ToolMessage(
            content=str(response), name=action.tool, tool_call_id=tool_call["id"]
        )

        # Add the function message to the list
        messages.append(function_message)

    # We return a list, because this will get added to the existing list

    return {"messages": messages}


# Define a new graph
workflow = StateGraph(AgentState)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("action", call_tool)

# Set the entrypoint as `agent`
# This means that this node is the first one called
workflow.set_entry_point("agent")

# We now add a conditional edge
workflow.add_conditional_edges(
    # First, we define the start node. We use `agent`.
    # This means these are the edges taken after the `agent` node is called.
    "agent",
    # Next, we pass in the function that will determine which node is called next.
    should_continue,
    # Finally we pass in a mapping.
    # The keys are strings, and the values are other nodes.
    # END is a special node marking that the graph should finish.
    # What will happen is we will call `should_continue`, and then the output of that
    # will be matched against the keys in this mapping.
    # Based on which one it matches, that node will then be called.
    {
        # If `tools`, then we call the tool node.
        "continue": "action",
        # Otherwise we finish.
        "end": END
    }
)

# We now add a normal edge from `tools` to `agent`.
# This means that after `tools` is called, `agent` node is called next.
workflow.add_edge('action', 'agent')

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
app = workflow.compile()


@tool
def home_assistant_memory_tool(query: str) -> str:
    """
    This assistant is able to store things in long term memory, postgres SQL database.
    Here is a list of tables this assistant currently in the database: user_profile, tasks, events, shopping_list, conversations, messages
    """
    # Call the model

    messages = [HumanMessage(content=query)]

    including_base_prompt = [SystemMessage(content=get_base_prompt())] + messages

    response = app.invoke({"messages": including_base_prompt})

    ai_reply = ""

    if response["messages"]:
        ai_reply = response["messages"][-1].content

    return ai_reply