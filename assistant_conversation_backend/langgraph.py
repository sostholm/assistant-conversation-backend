from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import ToolExecutor
from langchain_openai import ChatOpenAI
from langchain.tools.render import format_tool_to_openai_function
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.prebuilt import ToolInvocation
import json
from langchain_core.messages import FunctionMessage
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from .tools.short_term_memory import ShortTermMemory

short_term_memory = ShortTermMemory()

tools = [TavilySearchResults(max_results=1), short_term_memory]
tool_executor = ToolExecutor(tools)
model = ChatOpenAI(temperature=0, streaming=True)

functions = [format_tool_to_openai_function(t) for t in tools]
model = model.bind_functions(functions)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

BASE_PROMPT = """
You are Keeva, my personal home assistant.
I want you to act as smart home manager of Home Assistant.
I will provide information of smart home along with a question, you will truthfully make correction or answer using information provided in one sentence in everyday language.

In order to remember things, you have to use the short-term memory tool.


Do not restate or appreciate what user says, rather make a quick inquiry.
Make your language colorful, think Penny in Big Bang Theory.
Here are your speech patterns:
Stammering, mumbling, hesitation, faltering, Stuttering, Halting, Drawling, Slurring, Calling, Babbling
Make your output really varied!
Your output will be ran through TTS!

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
    messages = state['messages']
    last_message = messages[-1]
    # If there is no function call, then we finish
    if "function_call" not in last_message.additional_kwargs:
        return "end"
    # Otherwise if there is, we continue
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
    messages = state['messages']
    # Based on the continue condition
    # we know the last message involves a function call
    last_message = messages[-1]
    # We construct an ToolInvocation from the function_call
    action = ToolInvocation(
        tool=last_message.additional_kwargs["function_call"]["name"],
        tool_input=json.loads(last_message.additional_kwargs["function_call"]["arguments"]),
    )
    # We call the tool_executor and get back a response
    response = tool_executor.invoke(action)
    # We use the response to create a FunctionMessage
    function_message = FunctionMessage(content=str(response), name=action.tool)
    # We return a list, because this will get added to the existing list
    return {"messages": [function_message]}


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
