"""
Long-running tests for the AI assistant backend.
These tests verify the system's behavior over time with multiple messages and connections.

Note: These tests take longer to run than standard tests.
To run only these tests: pytest -xvs tests/test_long_running.py
"""

import pytest
import asyncio
import websockets
import json
import uuid
from datetime import datetime
import socket
import time

# Configuration
SERVER_HOST = "localhost"
SERVER_PORT = 8000
WEBSOCKET_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}/ws"

# Helper function to check if the server is running
def is_server_running():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((SERVER_HOST, SERVER_PORT)) == 0

# Skip all tests if the server isn't running
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not is_server_running(), reason="Backend server is not running")
]

# Test sustained communication
async def test_sustained_communication():
    """
    Test a longer session with multiple messages over time.
    This test simulates a real conversation with pauses between messages.
    """
    print("\nTesting sustained communication...")
    
    # Create a test device
    device_info = {
        "id": 300,
        "device_name": "Sustained Comm Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.300",
        "mac_address": "SU:ST:AI:NE:DC:OM",
        "location": "Living Room",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Connect to WebSocket
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        # Send device info
        await websocket.send(json.dumps(device_info))
        print("Device registered")
        
        # Wait before sending first message
        await asyncio.sleep(2)
        
        # Send first message
        message1 = [{
            "nickname": "long_test_user",
            "message": "Hello AI, how are you today?",
            "location": "Living Room"
        }]
        
        await websocket.send(json.dumps(message1))
        print("First message sent")
        
        # Wait for 5 seconds to simulate a pause in conversation
        await asyncio.sleep(5)
        
        # Send second message
        message2 = [{
            "nickname": "long_test_user",
            "message": "I'm wondering what the weather is like today.",
            "location": "Living Room"
        }]
        
        await websocket.send(json.dumps(message2))
        print("Second message sent")
        
        # Wait for 5 more seconds
        await asyncio.sleep(5)
        
        # Send third message from a different user
        message3 = [{
            "nickname": "another_user",
            "message": "Can you help us plan dinner tonight?",
            "location": "Living Room"
        }]
        
        await websocket.send(json.dumps(message3))
        print("Third message sent (from different user)")
        
        # Wait a final 5 seconds
        await asyncio.sleep(5)
        
        # Send final message
        message4 = [{
            "nickname": "long_test_user",
            "message": "Thanks for the information. I'll check in later.",
            "location": "Living Room"
        }]
        
        await websocket.send(json.dumps(message4))
        print("Final message sent")
        
        # Wait one more moment before disconnecting
        await asyncio.sleep(2)
        
        print("Sustained communication test completed")

# Test multiple concurrent connections
async def test_multiple_connections():
    """
    Test multiple concurrent connections from different devices.
    This test verifies the system can handle multiple connections simultaneously.
    """
    print("\nTesting multiple concurrent connections...")
    
    # Create three different devices
    device1_info = {
        "id": 301,
        "device_name": "Living Room Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.301",
        "mac_address": "MU:LT:IP:LE:01",
        "location": "Living Room",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    device2_info = {
        "id": 302,
        "device_name": "Kitchen Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.302",
        "mac_address": "MU:LT:IP:LE:02",
        "location": "Kitchen",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    device3_info = {
        "id": 303,
        "device_name": "Bedroom Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.303",
        "mac_address": "MU:LT:IP:LE:03",
        "location": "Bedroom",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Define a helper function for device communication
    async def device_communication(device_info, messages, location):
        """Handle communication for a single device"""
        device_name = device_info["device_name"]
        print(f"Starting communication for {device_name}")
        
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            # Register device
            await websocket.send(json.dumps(device_info))
            print(f"{device_name} registered")
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Send all messages with delays
            for i, msg_text in enumerate(messages):
                message = [{
                    "nickname": f"user_{location}",
                    "message": msg_text,
                    "location": location
                }]
                
                await websocket.send(json.dumps(message))
                print(f"{device_name} sent message {i+1}: {msg_text}")
                
                # Random delay between messages (1-3 seconds)
                delay = 1 + (i % 3)
                await asyncio.sleep(delay)
            
            # Keep connection open for a moment before closing
            await asyncio.sleep(2)
            print(f"{device_name} communication complete")
    
    # Define messages for each device
    living_room_messages = [
        "Hello from the living room",
        "What's on TV tonight?",
        "Can you dim the lights?"
    ]
    
    kitchen_messages = [
        "Hey AI, I'm in the kitchen",
        "What's a good recipe for dinner?",
        "How many calories in an apple?",
        "Set a timer for 5 minutes"
    ]
    
    bedroom_messages = [
        "Good evening from the bedroom",
        "What time is my first meeting tomorrow?",
        "Play some relaxing music"
    ]
    
    # Start all three device communications concurrently
    await asyncio.gather(
        device_communication(device1_info, living_room_messages, "Living Room"),
        device_communication(device2_info, kitchen_messages, "Kitchen"),
        device_communication(device3_info, bedroom_messages, "Bedroom")
    )
    
    print("Multiple connections test completed")

# Test connection persistence
async def test_connection_persistence():
    """
    Test that a connection can remain open for an extended period.
    This test verifies the system doesn't prematurely close long-lived connections.
    """
    print("\nTesting connection persistence...")
    
    # Create a test device
    device_info = {
        "id": 304,
        "device_name": "Persistence Test Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.304",
        "mac_address": "PE:RS:IS:TE:NC:E",
        "location": "Office",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Connect to WebSocket
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        # Send device info
        await websocket.send(json.dumps(device_info))
        print("Device registered")
        
        # Send an initial message
        initial_message = [{
            "nickname": "persistence_user",
            "message": "Hello, I'm starting a long session",
            "location": "Office"
        }]
        
        await websocket.send(json.dumps(initial_message))
        print("Initial message sent")
        
        # Keep the connection open for 30 seconds, sending a message every 10 seconds
        start_time = time.time()
        message_count = 1
        
        while time.time() - start_time < 30:
            # Wait 10 seconds between messages
            await asyncio.sleep(10)
            
            # Send another message
            message_count += 1
            next_message = [{
                "nickname": "persistence_user",
                "message": f"I'm still here, message #{message_count}",
                "location": "Office"
            }]
            
            await websocket.send(json.dumps(next_message))
            print(f"Message #{message_count} sent after {int(time.time() - start_time)} seconds")
        
        # Send a final message
        final_message = [{
            "nickname": "persistence_user",
            "message": "Ending my long session now",
            "location": "Office"
        }]
        
        await websocket.send(json.dumps(final_message))
        print("Final message sent")
        
        # Wait a moment before disconnecting
        await asyncio.sleep(1)
        
        print(f"Connection remained open for {int(time.time() - start_time)} seconds")