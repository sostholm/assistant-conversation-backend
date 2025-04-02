import unittest
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from assistant_conversation_backend.models.groq_thinker import GroqThinker
from assistant_conversation_backend.models.base_model import UserAction, AIAgentAction, ToolAction


class TestGroqThinkerParsing(unittest.TestCase):
    def setUp(self):
        # Create the thinker without initializing API client
        with patch.dict(os.environ, {"GROQ_API_KEY": "dummy_key"}):
            self.thinker = GroqThinker()
    
    def test_parse_xml_format(self):
        """Test parsing responses in XML format."""
        response = """
        <chat>
            <user_message user=Jennifer device=living_room>Hey Jennifer, how's it going?</user_message>
            <agent_message agent=HomeAssistant>Checking the temperature</agent_message>
            <tool_command command="/search" arguments="weather forecast for today">Use search to check weather</tool_command>
        </chat>
        """
        
        actions = self.thinker.parse_response(response)
        
        # Verify user actions
        self.assertEqual(len(actions.user_actions), 1)
        self.assertEqual(actions.user_actions[0].recipient, "Jennifer")
        self.assertEqual(actions.user_actions[0].device, "living_room")
        self.assertEqual(actions.user_actions[0].message, "Hey Jennifer, how's it going?")
        
        # Verify agent actions
        self.assertEqual(len(actions.ai_agent_actions), 1)
        self.assertEqual(actions.ai_agent_actions[0].recipient, "HomeAssistant")
        self.assertEqual(actions.ai_agent_actions[0].message, "Checking the temperature")
        
        # Verify tool actions
        self.assertEqual(len(actions.tools_actions), 1)
        self.assertEqual(actions.tools_actions[0].command, "/search")
        self.assertEqual(actions.tools_actions[0].arguments, "weather forecast for today")
    
    def test_parse_mentions_format(self):
        """Test parsing responses in @mentions format."""
        response = """
        <chat>
            @Jennifer [device:living_room] Hey Jennifer, how's it going?
            @HomeAssistantAgent Check the temperature in the living room
            /search weather forecast for today
        </chat>
        """
        
        actions = self.thinker.parse_response(response)
        
        # Verify user actions
        self.assertEqual(len(actions.user_actions), 1)
        self.assertEqual(actions.user_actions[0].recipient, "Jennifer")
        self.assertEqual(actions.user_actions[0].device, "living_room")
        self.assertEqual(actions.user_actions[0].message, "Hey Jennifer, how's it going?")
        
        # Verify agent actions
        self.assertEqual(len(actions.ai_agent_actions), 1)
        self.assertEqual(actions.ai_agent_actions[0].recipient, "HomeAssistantAgent")
        self.assertEqual(actions.ai_agent_actions[0].message, "Check the temperature in the living room")
        
        # Verify tool actions
        self.assertEqual(len(actions.tools_actions), 1)
        self.assertEqual(actions.tools_actions[0].command, "/search")
        self.assertEqual(actions.tools_actions[0].arguments, "weather forecast for today")
    
    def test_parse_quoted_arguments(self):
        """Test parsing with quoted arguments."""
        response = """
        <chat>
            <tool_command command="/search" arguments="weather forecast for 'New York City'">Search with single quotes</tool_command>
            <tool_command command='/calculate' arguments="2 + 2 * (3 - 1)">Calculate with double quotes</tool_command>
            /remind "Call Mom" at 5pm tomorrow
            /weather "New York City" --format=detailed
        </chat>
        """
        
        actions = self.thinker.parse_response(response)
        
        # Check all actions are present
        self.assertEqual(len(actions.tools_actions), 4)
        
        # Find actions by command rather than relying on specific order
        search_actions = [a for a in actions.tools_actions if a.command == "/search"]
        calculate_actions = [a for a in actions.tools_actions if a.command == "/calculate"]
        remind_actions = [a for a in actions.tools_actions if a.command == "/remind"]
        weather_actions = [a for a in actions.tools_actions if a.command == "/weather"]
        
        # Verify tool actions from XML format
        self.assertEqual(len(search_actions), 1)
        self.assertEqual(search_actions[0].arguments, "weather forecast for 'New York City'")
        
        self.assertEqual(len(calculate_actions), 1)
        self.assertEqual(calculate_actions[0].arguments, "2 + 2 * (3 - 1)")
        
        # Verify slash commands with quoted arguments
        self.assertEqual(len(remind_actions), 1)
        self.assertEqual(remind_actions[0].arguments, "Call Mom at 5pm tomorrow")
        
        self.assertEqual(len(weather_actions), 1)
        self.assertEqual(weather_actions[0].arguments, "New York City --format=detailed")
    
    def test_mixed_formats(self):
        """Test parsing responses with mixed formats."""
        response = """
        <chat>
            <user_message user=Jennifer device=living_room>Hey Jennifer!</user_message>
            @HomeAssistantAgent Check the temperature
            /search best restaurants in town
        </chat>
        """
        
        actions = self.thinker.parse_response(response)
        
        # Verify user actions from XML format
        self.assertEqual(len(actions.user_actions), 1)
        self.assertEqual(actions.user_actions[0].recipient, "Jennifer")
        
        # Verify agent actions from @mentions
        self.assertEqual(len(actions.ai_agent_actions), 1)
        self.assertEqual(actions.ai_agent_actions[0].recipient, "HomeAssistantAgent")
        
        # Verify tool actions from slash commands
        self.assertEqual(len(actions.tools_actions), 1)
        self.assertEqual(actions.tools_actions[0].command, "/search")
    
    def test_complex_tool_commands(self):
        """Test parsing complex tool commands with various argument formats."""
        response = """
        <chat>
            /search "restaurants in 'New York'" --sort=rating --limit=5
            /calendar add "Doctor's appointment" 2024-05-15T14:30:00 --location="Medical Center"
            /translate "Hello world" --from=en --to=fr
        </chat>
        """
        
        actions = self.thinker.parse_response(response)
        
        self.assertEqual(len(actions.tools_actions), 3)
        
        # Command 1
        self.assertEqual(actions.tools_actions[0].command, "/search")
        self.assertEqual(actions.tools_actions[0].arguments, "restaurants in 'New York' --sort=rating --limit=5")
        
        # Command 2
        self.assertEqual(actions.tools_actions[1].command, "/calendar")
        self.assertEqual(actions.tools_actions[1].arguments, "add Doctor's appointment 2024-05-15T14:30:00 --location=Medical Center")
        
        # Command 3
        self.assertEqual(actions.tools_actions[2].command, "/translate")
        self.assertEqual(actions.tools_actions[2].arguments, "Hello world --from=en --to=fr")
    
    def test_parse_error_handling(self):
        """Test error handling for invalid formats."""
        # No valid actions should raise ValueError
        with self.assertRaises(ValueError):
            self.thinker.parse_response("This is an invalid response with no actions")
        
        # Missing device for user message should raise ValueError
        with self.assertRaises(ValueError):
            self.thinker.parse_response("<chat>@Jennifer Hello without device</chat>")


class TestGroqThinkerGenerate(unittest.TestCase):
    @patch('openai.AsyncOpenAI')
    def test_generate_success(self, mock_client):
        """Test successful generation."""
        # Mock setup
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = """
        <chat>
            <user_message user=User device=phone>This is a test message</user_message>
        </chat>
        """
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        # Use AsyncMock to properly mock an async method
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Create thinker with mock
        with patch.dict(os.environ, {"GROQ_API_KEY": "dummy_key"}):
            thinker = GroqThinker()
        
        # Test
        import asyncio
        actions = asyncio.run(thinker._generate("Test prompt"))
        
        # Verify
        self.assertEqual(len(actions.user_actions), 1)
        self.assertEqual(actions.user_actions[0].recipient, "User")
        self.assertEqual(actions.user_actions[0].message, "This is a test message")


if __name__ == '__main__':
    unittest.main()
