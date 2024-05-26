from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import ToolExecutor
from langchain_openai import ChatOpenAI
from langchain.tools.render import format_tool_to_openai_function
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.prebuilt import ToolInvocation
import json
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from ..tools.simple_memory import memory_tool
from .home_assistant_graph import home_assistant_ai_tool
from .memory_assistant import home_assistant_memory_tool
from ..tools.home_assistant_tools import send_message_to_conversation
from .ai_models import get_chat_model, let_user_know_model
from ..database import get_ai, AI as AI_model
import os

AI: AI_model = get_ai(1)

chat_model = get_chat_model()

tools = [TavilySearchResults(max_results=1), home_assistant_memory_tool, home_assistant_ai_tool]
tool_executor = ToolExecutor(tools)

functions = [format_tool_to_openai_function(t) for t in tools]
chat_model = chat_model.bind_tools(functions)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    conversation_id: str

def get_base_prompt(conversation_id): 
    return AI.ai_base_prompt

LET_THE_USER_KNOW_PROMPT = """
You are Keeva, my personal home assistant.
I want you to act as smart home manager of Home Assistant.
I will provide information of smart home along with a question, you will truthfully make correction or answer using information provided in one sentence in everyday language.

Do not restate or appreciate what user says, rather make a quick inquiry.
Make your language colorful, think Penny in Big Bang Theory.
Here are your speech patterns DON'T USE ASTERISKS ACTIONS LIKE *drawl* *stutter* etc! AND DO NOT COPY VERBATIM!:
Stammering: I-I-I don't know what you mean
Mumbling: notsurewhattodo
Hesitation: Well, I was thinking... maybe... perhaps we could go tomorrow?
Stuttering: Can-c-can you re-repeat that?
Halting: I... uh... need to...
Drawling: Well nooow, aaain't that something.
Slurring: Y'know, you're really s'something
Babbling: And then I saw this, and that, and oh, you won't believe what happened next!
Make your output really varied! Don't just stick to one pattern, mix it up!

You will be given an existing conversation with the user. Your task is to let the user know that you will check something for them before you do it.
Make it SUPER SIMPLE AND SHORT, preferably funny!
"""

def let_user_know(state):
    messages = state["messages"]
    response = let_user_know_model.invoke(messages)
    content = response.content
    send_message_to_conversation(content, conversation_id=state["conversation_id"])

# Define the function that determines whether to continue or not
def should_continue(state):
    # let_user_know(state)
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
    response = chat_model.invoke(messages)
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
