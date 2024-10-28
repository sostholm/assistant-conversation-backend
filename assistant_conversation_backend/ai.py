from langchain_core.messages import HumanMessage, FunctionMessage, AIMessage, SystemMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import ToolExecutor
from .ai_graphs.chat_graph import app, get_base_prompt
from starlette.responses import JSONResponse
from starlette.requests import Request
from .database import add_or_update_conversation
from magentic import prompt, ParallelFunctionCall, AssistantMessage, UserMessage, SystemMessage, FunctionCall, FunctionResultMessage


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

    including_base_prompt = [SystemMessage(content=get_base_prompt(conversation_id=data["conversation_id"]))] + messages

    response = app.invoke({"messages": including_base_prompt, "conversation_id": data["conversation_id"]})

    print(response)

    if response["messages"]:
        ai_reply = response["messages"][-1].content

    response = {"role": "assistant", "content": ai_reply}

    conversation =  data["messages"] + [response]

    add_or_update_conversation(data["conversation_id"], conversation)

    # Return the response
    return JSONResponse(response)
