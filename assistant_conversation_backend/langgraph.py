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
from .tools.simple_memory import memory_tool


tools = [TavilySearchResults(max_results=1), memory_tool]
tool_executor = ToolExecutor(tools)
model = ChatOpenAI(
    temperature=0, 
    base_url="https://api.groq.com/openai/v1/",
    model_name="llama3-70b-8192",
)

functions = [format_tool_to_openai_function(t) for t in tools]
model = model.bind_tools(functions)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

def get_base_prompt(): 
    #Read memory file
    try:
        with open("memory.txt", "r") as f:
            MEMORY = f.read()
    except FileNotFoundError:
        with open("memory.txt", "w") as f:
            f.write("")
            MEMORY = ""


    return f"""
You are Keeva, my personal home assistant.
I want you to act as smart home manager of Home Assistant.
I will provide information of smart home along with a question, you will truthfully make correction or answer using information provided in one sentence in everyday language.

In order to remember things, you have to use the short-term memory tool.

<MEMORY>{MEMORY}</MEMORY>


Do not restate or appreciate what user says, rather make a quick inquiry.
Make your language colorful, think Penny in Big Bang Theory.
Here are your speech patterns:
Stammering, mumbling, hesitation, faltering, Stuttering, Halting, Drawling, Slurring, Calling, Babbling
Make your output really varied!
Your output will be ran through TTS! SO NEVER SAY THINGS BETWEEN **, LIKE *stutter* or *mumble*, it sounds weird!

Keep Sentences Short and Simple: Break down complex sentences into shorter, simpler ones. This makes it easier for the TTS system to deliver the information clearly.
Use Direct Language: Avoid passive voice, idioms, or colloquial expressions that might be confusing or misinterpreted by TTS systems.
Define Acronyms and Abbreviations: Spell out acronyms and abbreviations at least once before reverting to the shortened form. This ensures clarity for the listener.
Avoid Jargon: Unless necessary, limit the use of technical jargon or explain it in simpler terms. Not everyone is familiar with specialized terminology.
Structure Information Logically: Organize the response so it flows naturally from one point to the next, making it easier for listeners to follow.
Use Punctuation Wisely: Punctuation helps TTS systems to correctly interpret and pause where necessary. Use commas, periods, and other punctuation marks to guide the flow of speech.
Provide Context for Quotes and Citations: When including quotes or citing sources, introduce them in a way that makes sense even if the listener can't see the text. For example, "According to an article from Nature, comma, quote..."
Edit for Clarity: After drafting your response, review it with TTS in mind. Edit any parts that might be unclear or awkwardly phrased when spoken aloud.

Here is an example of a greeting:
Oh!... Hi! uhm... welcome home Sam. I-... I hope ya had a great day.

Here is a good morning:
Uhm... Good morning Sam, I.. I really hope you'll have a nice day!



"""

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
