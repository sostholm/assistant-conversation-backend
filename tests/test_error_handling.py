"""
Tests for error handling in the AI assistant backend.
These tests verify how the system handles various error conditions.
"""

import pytest
import asyncio
import websockets
import json
import uuid
from datetime import datetime
import socket
import aiohttp
import time

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

# Test missing required fields in HTTP request
async def test_http_missing_fields():
    """Test that the HTTP endpoint properly handles missing required fields."""
    print("\nTesting HTTP endpoint with missing fields...")
    
    # Create an event missing the required nickname field
    incomplete_event = {
        "message": "This message is missing nickname"
        # No nickname field
    }
    
    # Send the incomplete request
    async with aiohttp.ClientSession() as session:
        async with session.post(HTTP_URL, json=incomplete_event) as response:
            # Should return 400 Bad Request
            assert response.status == 400, f"Expected status 400, got {response.status}"
            
            # Check the error response
            error_data = await response.json()
            print(f"Error response: {error_data}")
            assert "error" in error_data

# Test invalid JSON in WebSocket message
async def test_websocket_invalid_json():
    """Test how the WebSocket handles invalid JSON."""
    print("\nTesting WebSocket with invalid JSON...")
    
    # Create a valid device for registration
    device_info = {
        "id": 200,
        "device_name": "Error Test Device",
        "device_type_id": 1,
        "unique_identifier": str(uuid.uuid4()),
        "ip_address": "192.168.1.200",
        "mac_address": "ER:RO:RT:ES:TD:EV",
        "location": "Error Test Room",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Connect to WebSocket
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        # Send valid device info
        await websocket.send(json.dumps(device_info))
        print("Device registered")
        
        # Send invalid JSON
        try:
            await websocket.send("This is not valid JSON")
            print("Invalid JSON sent")
            
            # Wait to see if the connection is still alive
            await asyncio.sleep(1)
            
            # Try to send a valid message to check if the connection is still open
            valid_message = [{
                "nickname": "error_test_user",
                "message": "Testing after invalid JSON",
                "location": "Error Test Room"
            }]
            
            await websocket.send(json.dumps(valid_message))
            print("Valid message sent after invalid JSON")
            
            # If we got here, the connection survived the invalid JSON
            # This is good - the server should be robust to message errors
        except websockets.exceptions.ConnectionClosed:
            # The server may have chosen to close the connection on invalid input
            # This is also a valid approach, but we should note it
            print("Server closed connection on invalid JSON")
