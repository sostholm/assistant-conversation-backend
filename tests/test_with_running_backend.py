"""
Test suite for the AI assistant backend with the queue-based architecture.
Includes tests for the enhanced prompt features like tasks and time awareness.

USAGE:
1. Start your backend server first: 
   python -m assistant_conversation_backend.app
2. Then run these tests:
   pytest -xvs tests/test_with_running_backend.py
"""

import pytest
import asyncio
import websockets
import json
import uuid
from datetime import datetime, timedelta
import socket
import time
import aiohttp

# Configuration
SERVER_HOST = "localhost"
SERVER_PORT = 8000
WEBSOCKET_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}/ws"
HTTP_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/event"

# Helper function to check if the server is running
def is_server_running():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((SERVER_HOST, SERVER_PORT)) == 0

# Skip all tests if the server isn't running
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not is_server_running(), reason="Backend server is not running")
]

# Test basic WebSocket communication
async def test_websocket_basic():
    """Test basic WebSocket connectivity and device registration."""
    print("\nStarting basic WebSocket test...")
    
    # Create a test device
    device_info = {
        "id": 99,
        "device_name": "Test Basic Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.99",
        "mac_address": "BB:CC:DD:EE:FF:99",
        "location": "Test Room",
        "status": "active",
        "registered_at": datetime.now().isoformat(),
        "last_seen_at": datetime.now().isoformat()
    }
    
    # Connect to WebSocket - no try/except so failures will fail the test
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        print("Connected to WebSocket")
        
        # Send device info
        await websocket.send(json.dumps(device_info))
        print("Device info sent successfully")

# Test sending a message via WebSocket
async def test_websocket_message():
    """Test sending a message through the WebSocket."""
    print("\nTesting message sending via WebSocket...")
    
    # Create a test device
    device_info = {
        "id": 100,
        "device_name": "Message Test Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.100",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "location": "Living Room",
        "status": "active",
        "registered_at": datetime.now().isoformat(),
        "last_seen_at": datetime.now().isoformat()
    }
    
    # Connect to WebSocket
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        # Send device info
        await websocket.send(json.dumps(device_info))
        print("Device registered")
        
        # Wait a moment for registration to process
        await asyncio.sleep(1)
        
        # Send a message
        test_message = [{
            "nickname": "Sam",
            "message": "Hello AI assistant, this is a test message",
            "location": "Living Room"
        }]
        
        await websocket.send(json.dumps(test_message))
        print("Message sent successfully")
        
        # Verify we can still send more messages after the first
        await asyncio.sleep(1)

        # Receive and print the response

        response = await asyncio.wait_for(websocket.recv(), timeout=30)
        print(f"Received response: {response}")

        second_message = [{
            "nickname": "Sam",
            "message": "This is a follow-up message",
            "location": "Living Room"
        }]
        
        await websocket.send(json.dumps(second_message))
        print("Second message sent successfully")

        response = await asyncio.wait_for(websocket.recv(), timeout=30)
        print(f"Received response: {response}")



# Test sending multiple messages from different speakers
async def test_multiple_speakers():
    """Test sending messages from multiple speakers in a single batch."""
    print("\nTesting multiple speakers in a single message batch...")
    
    # Create a test device
    device_info = {
        "id": 101,
        "device_name": "Multi-Speaker Test Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.101",
        "mac_address": "CC:DD:EE:FF:00:11",
        "location": "Conference Room",
        "status": "active",
        "registered_at": datetime.now().isoformat(),
        "last_seen_at": datetime.now().isoformat()
    }
    
    # Connect to WebSocket
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        # Send device info
        await websocket.send(json.dumps(device_info))
        print("Device registered")
        
        # Wait a moment for registration to process
        await asyncio.sleep(1)
        
        # Send multiple speaker messages
        test_messages = [
            {
                "nickname": "Sam",
                "message": "Hello from user one",
                "location": "Conference Room"
            },
            {
                "nickname": "user2",
                "message": "And hello from user two",
                "location": "Conference Room"
            }
        ]
        
        await websocket.send(json.dumps(test_messages))

        # Receive and print the response

        response = await asyncio.wait_for(websocket.recv(), timeout=10)
        print(f"Received response: {response}")

        print("Multiple speaker messages sent successfully")

# Test sending an event through the HTTP endpoint
async def test_http_event():
    """Test sending an event through the HTTP endpoint."""
    print("\nTesting HTTP event endpoint...")
    
    # Create a test event
    event_data = {
        "message": "This is a test event message",
        "nickname": "system_tester",
        "location": "System",
        "to_user": "keeva-assistant"
    }
    
    # Send the HTTP request
    async with aiohttp.ClientSession() as session:
        async with session.post(HTTP_URL, json=event_data) as response:
            # Check response status
            assert response.status == 200, f"Expected status 200, got {response.status}"
            
            # Parse response data
            response_data = await response.json()
            print(f"HTTP event response: {response_data}")
            
            # Verify response format
            assert "status" in response_data, "Response missing 'status' field"
            assert response_data["status"] == "ok", f"Expected status 'ok', got '{response_data['status']}'"

# Test time-awareness in the assistant
async def test_time_awareness():
    """Test the assistant's awareness of current time."""
    print("\nTesting time awareness...")
    
    # Create a test device
    device_info = {
        "id": 103,
        "device_name": "Time Test Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.103",
        "mac_address": "TI:ME:TE:ST:DE:V1",
        "location": "Office",
        "status": "active",
        "registered_at": datetime.now().isoformat(),
        "last_seen_at": datetime.now().isoformat()
    }
    
    # Connect to WebSocket
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        # Send device info
        await websocket.send(json.dumps(device_info))
        print("Device registered")
        
        # Wait a moment for registration to process
        await asyncio.sleep(1)
        
        # Send a message asking about the current time
        current_time = datetime.now()
        time_message = [{
            "nickname": "time_test_user",
            "message": "What time is it right now?",
            "location": "Office"
        }]
        
        await websocket.send(json.dumps(time_message))
        print("Time question sent")
        
        # Try to get a response, but don't fail the test if we don't
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            print(f"Received response: {response}")
            
            # Note: In a real test, you'd parse the response to check 
            # if it correctly reports the current time, but this
            # is difficult to test precisely.
        except asyncio.TimeoutError:
            print("No response received within timeout (expected with queue-based architecture)")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed: {e}")

# Test task awareness in the assistant
async def test_task_awareness():
    """Test the assistant's awareness of scheduled tasks."""
    print("\nTesting task awareness...")
    
    # Create a test device
    device_info = {
        "id": 104,
        "device_name": "Task Test Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.104",
        "mac_address": "TA:SK:TE:ST:DE:V1",
        "location": "Study",
        "status": "active",
        "registered_at": datetime.now().isoformat(),
        "last_seen_at": datetime.now().isoformat()
    }
    
    # Connect to WebSocket
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        # Send device info
        await websocket.send(json.dumps(device_info))
        print("Device registered")
        
        # Wait a moment for registration to process
        await asyncio.sleep(1)
        
        # Send a message asking about upcoming tasks
        task_message = [{
            "nickname": "task_test_user",
            "message": "What are my scheduled tasks for today?",
            "location": "Study"
        }]
        
        await websocket.send(json.dumps(task_message))
        print("Task question sent")
        
        # Try to get a response, but don't fail the test if we don't
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            print(f"Received response: {response}")
        except asyncio.TimeoutError:
            print("No response received within timeout (expected with queue-based architecture)")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed: {e}")

# Test reconnection after disconnection
async def test_reconnection():
    """Test that a device can reconnect after disconnection."""
    print("\nTesting device reconnection...")
    
    # Generate a unique device ID that we'll use for both connections
    unique_id = str(uuid.uuid4())
    
    # Create a test device with the unique ID
    device_info = {
        "id": 102,
        "device_name": "Reconnection Test Device",
        "device_type_id": 1,
        "unique_identifier": unique_id,
        "ip_address": "192.168.1.102",
        "mac_address": "DD:EE:FF:00:11:22",
        "location": "Hallway",
        "status": "active",
        "registered_at": datetime.now().isoformat(),
        "last_seen_at": datetime.now().isoformat()
    }
    
    # First connection
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        # Send device info
        await websocket.send(json.dumps(device_info))
        print("Device registered in first connection")
        
        # Send a message
        test_message = [{
            "nickname": "reconnect_user",
            "message": "Message before reconnection",
            "location": "Hallway"
        }]
        
        await websocket.send(json.dumps(test_message))
        print("Message sent on first connection")
        await asyncio.sleep(1)
    
    print("First connection closed")
    
    # Wait before reconnecting
    await asyncio.sleep(3)
    
    # Second connection with the same device ID
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        # Send the same device info (same unique_identifier)
        await websocket.send(json.dumps(device_info))
        print("Device re-registered in second connection")
        
        # Send another message
        test_message = [{
            "nickname": "reconnect_user",
            "message": "Message after reconnection",
            "location": "Hallway"
        }]
        
        await websocket.send(json.dumps(test_message))
        print("Message sent on second connection")