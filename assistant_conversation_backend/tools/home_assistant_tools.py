import requests
from typing import List
from pydantic import BaseModel, Field
import os
import asyncio

HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN")
HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL")

# Constants for the Home Assistant URL and Token
BASE_URL = HOME_ASSISTANT_URL
HEADERS = {
    "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
    "content-type": "application/json",
}


def get_all_entity_ids() -> List[str]:
    """Fetches all entity IDs from Home Assistant."""
    url = f"{BASE_URL}/states"
    response = requests.get(url, headers=HEADERS, verify=False)
    data = response.json()
    entity_ids = [entity['entity_id'] for entity in data]
    return entity_ids

class GetEntityStatesInput(BaseModel):
    """Input for the get_entity_states tool."""
    entity_ids: List[str] = Field(description="List of entity IDs to fetch states for.")


def get_entity_states(entity_ids) -> List[dict]:
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

def set_entity_state(entity_id, new_state, attributes=None) -> bool:
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

def send_message_to_conversation(message, conversation_id=None, agent_id=None) -> bool:
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

async def ask_home_assistant(message: str) -> str:
    """
    Sends a message to the Home Assistant conversation with optional context parameters.
    """
    url = f"{BASE_URL}/conversation/process"
    data = {"text": message}
    
    data['agent_id'] = "261036381fb56fe719dac933c703ff68"
    
    response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.post(url, data, headers=HEADERS, verify=False))

    if response.status_code != 200:
        return f"Unable to get response from Home Assistant. {response.status_code}, [{response.text}]"
    
    data = response.json()

    message = data["response"]["speech"]["plain"]["speech"]
    return message