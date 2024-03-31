from langchain_core.messages import HumanMessage, FunctionMessage, AIMessage, SystemMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import ToolExecutor
from time import time
from .langgraph import app
from starlette.responses import PlainTextResponse
from starlette.requests import Request

tools = [TavilySearchResults(max_results=1)]
tool_executor = ToolExecutor(tools)

def convert_message(messages):
    converted_messages = []
    for message in messages:

        if isinstance(message, str):
            print(message)

        if message['role'] in ["human", "user"]:
            converted_messages.append(HumanMessage(content=message["content"]))
        elif message['role'] in ["function"]:
            converted_messages.append(FunctionMessage(content=message["content"]))
        elif message['role'] in ["ai", 'assistant']:
            converted_messages.append(AIMessage(content=message["content"]))
    
    return converted_messages



async def assistant_response(request: Request):
    # Get the text from the POST request
    data = await request.json()
    # Call the model
    
    messages = convert_message(data["messages"])

    response = app.invoke({"messages": messages})

    print(response)

    if response["messages"]:
        ai_reply = response["messages"][-1].content

    # Return the response
    return PlainTextResponse(ai_reply)
