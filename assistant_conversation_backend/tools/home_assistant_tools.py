import requests
import json
from typing import List
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import tool, StructuredTool
import os

HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN")
HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL")

# Constants for the Home Assistant URL and Token
BASE_URL = HOME_ASSISTANT_URL
HEADERS = {
    "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
    "content-type": "application/json",
}

# @tool("get_home_assistant_entity_states", return_direct=False)
def get_all_entity_ids():
    """Fetches all entity IDs from Home Assistant."""
    url = f"{BASE_URL}/states"
    response = requests.get(url, headers=HEADERS, verify=False)
    data = response.json()
    entity_ids = [entity['entity_id'] for entity in data]
    return entity_ids

class GetEntityStatesInput(BaseModel):
    """Input for the get_entity_states tool."""
    entity_ids: List[str] = Field(description="List of entity IDs to fetch states for.")

# @tool("get_home_assistant_entity_states", args_schema=GetEntityStatesInput, return_direct=False)
def get_entity_states(entity_ids):
    """Fetches states for a list of entity IDs."""
    entity_states = []
    for entity_id in entity_ids:
        url = f"{BASE_URL}/states/{entity_id}"
        response = requests.get(url, headers=HEADERS, verify=False)
        data = response.json()
        
        entity_states.append(data)
    return entity_states

class SetEntityStatesInput(BaseModel):
    """Input for the set_entity_states tool."""
    entity_id: str = Field(description="The ID of the entity to modify.")
    new_state: str = Field(description="The new state value.")
    attributes: dict = Field(default=None, description="Additional attributes to set for the entity.")

def set_entity_state(entity_id, new_state, attributes=None):
    """
    Changes the state of an entity in Home Assistant.
    
    Args:
        entity_id (str): The ID of the entity to modify.
        new_state (str): The new state value.
        attributes (dict): Optional. Additional attributes to set for the entity.
    
    Returns:
        bool: True if the state was updated successfully, False otherwise.
    """
    url = f"{BASE_URL}/states/{entity_id}"
    data = {"state": new_state}
    if attributes:
        data['attributes'] = attributes
    
    response = requests.post(url, headers=HEADERS, json=data, verify=False)
    return response.status_code == 200

class SendMessageToConversationInput(BaseModel):
    """Input for the send_message_to_conversation tool."""
    message: str = Field(description="The ID of the entity to modify.")
    new_state: str = Field(description="The new state value.")

def send_message_to_conversation(message, conversation_id=None, agent_id=None):
    """
    Sends a message to the Home Assistant conversation with optional context parameters.
    """
    url = f"{BASE_URL}/services/conversation/process"
    data = {"text": message}
    
    if conversation_id:
        data['conversation_id'] = conversation_id
    
    if agent_id:
        data['agent_id'] = agent_id
    
    response = requests.post(url, headers=HEADERS, json=data, verify=False)

    return response.status_code == 200
    

class AskHomeAssistantInput(BaseModel):
    """Input for the ask_home_assistant tool."""
    message: str = Field(description="The message to send to the Home Assistant conversation.")

def ask_home_assistant(message: str):
    """
    Sends a message to the Home Assistant conversation with optional context parameters.
    """
    url = f"{BASE_URL}/conversation/process"
    data = {"text": message}
    
    data['agent_id'] = "261036381fb56fe719dac933c703ff68"
    
    response = requests.post(url, headers=HEADERS, json=data, verify=False)

    if response.status_code != 200:
        return False
    
    data = response.json()

    message = data["response"]["speech"]["plain"]["speech"]
    return message

get_all_entity_ids_tool = StructuredTool.from_function(
    func=get_all_entity_ids,
    name="get_home_assistant_entity_ids",
    description="Fetches all entity IDs from Home Assistant.",
    # coroutine= ... <- you can specify an async method if desired as well
    return_direct=False,
)

get_entity_states_tool = StructuredTool.from_function(
    func=get_entity_states,
    name="get_home_assistant_entity_states",
    description="Fetches states for a list of entity IDs from Home Assistant",
    # coroutine= ... <- you can specify an async method if desired as well
    args_schema=GetEntityStatesInput,
    return_direct=False,
)

set_entity_state_tool = StructuredTool.from_function(
    func=set_entity_state,
    name="set_home_assistant_entity_states",
    description="Changes the state of an entity in Home Assistant.",
    # coroutine= ... <- you can specify an async method if desired as well
    args_schema=SetEntityStatesInput,
    return_direct=False,
)

send_message_to_conversation_tool = StructuredTool.from_function(
    func=send_message_to_conversation,
    name="send_message_to_conversation",
    description="Send messages to the user, letting them know what you're doing before you do it.",
    # coroutine= ... <- you can specify an async method if desired as well
    args_schema=SetEntityStatesInput,
    return_direct=False,
)

ask_home_assistant_tool = StructuredTool.from_function(
    func=ask_home_assistant,
    name="ask_home_assistant",
    description="This tool is a Home Assistant AI that can answer questions about the smart home and perform actions. This assistant have full access to the Home Assistant API and can perform actions on the smart home.",
    # coroutine= ... <- you can specify an async method if desired as well
    args_schema=AskHomeAssistantInput,
    return_direct=False,
)