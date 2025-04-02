from openai import AsyncOpenAI
import os
from .base_model import BaseAIModel, Actions, UserAction, AIAgentAction


class GroqThinker(BaseAIModel):
    def __init__(self, model_name: str = "qwen-qwq-32b"):
        self.result_format_prompt = """
Your final response should be enclosed within <chat></chat> tags.
1-3 messages. ONLY SEND A SINGLE MESSAGE TO A SINGLE USER! Multiple messages to the same tool is ok. Remember it will be spoken using STT!
Each line should be a separate <message></message> tag.
The format should be as follows:
<chat>
    <user_message user=user device=device_name>First message</user_message>
    <agent_message agent=agent_name>Second message</agent_message>
</chat>

IMPORTANT: Agents MUST NOT message themselves! For example, if you are Keeva, do not create messages from Keeva to Keeva.

Format to route message to users:
example when user is in living room:
<user_message user=Jennifer device=living_room>Hey Jennifer, how's it going?</user_message>
example when user is in kitchen:
<user_message user=Jennifer device=kitchen>Hey Jennifer, how's it going?</user_message>

ALSO Don't overthink!
3 symptoms of overthinking

analysis paralysis: excessive planning, generating long reasoning chains with minimal concrete actions or progress in the environment

rogue actions: executing multiple actions in a single turn without waiting for environmental feedback, assuming success based on internal simulation

premature disengagement: terminating a task based on internal assessment rather than actual environmental state or feedback
"""
        self.model = model_name
        self.client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ["GROQ_API_KEY"],
        )

    def parse_response(self, response: str) -> Actions:
        response = response.replace("<chat>", "").replace("</chat>", "").strip()
        
        user_actions = []
        ai_agent_actions = []

        # Extract user_message tags
        user_msg_start = response.find("<user_message")
        while user_msg_start != -1:
            user_msg_end = response.find("</user_message>", user_msg_start)
            if user_msg_end == -1:
                raise ValueError("Malformed response: missing </user_message> closing tag")
            
            user_msg = response[user_msg_start:user_msg_end + len("</user_message>")]
            
            # Extract attributes
            user_attr = user_msg.split(">")[0]
            user_match = user_attr.find("user=")
            device_match = user_attr.find("device=")
            
            if user_match == -1 or device_match == -1:
                raise ValueError("Malformed user_message: missing user or device attributes")
            
            # Extract username (between user= and next space or device=)
            if device_match > user_match:
                username = user_attr[user_match+5:device_match].strip().rstrip('=').strip()
            else:
                username = user_attr[user_match+5:].split()[0].strip()
            
            # Extract device name (between device= and > or end of attributes)
            device_name = user_attr[device_match+7:].split()[0].strip().rstrip('>').strip()
            
            # Extract message content (between > and </user_message>)
            content_start = user_msg.find(">") + 1
            content_end = user_msg.rfind("<")
            message_content = user_msg[content_start:content_end].strip()
            
            user_actions.append(
                UserAction(message=message_content, recipient=username, device=device_name)
            )
            
            # Find the next user_message tag
            user_msg_start = response.find("<user_message", user_msg_end)
        
        # Extract agent_message tags
        agent_msg_start = response.find("<agent_message")
        while agent_msg_start != -1:
            agent_msg_end = response.find("</agent_message>", agent_msg_start)
            if agent_msg_end == -1:
                raise ValueError("Malformed response: missing </agent_message> closing tag")
            
            agent_msg = response[agent_msg_start:agent_msg_end + len("</agent_message>")]
            
            # Extract agent name
            agent_attr = agent_msg.split(">")[0]
            agent_match = agent_attr.find("agent=")
            
            if agent_match == -1:
                raise ValueError("Malformed agent_message: missing agent attribute")
            
            agent_name = agent_attr[agent_match+6:].split()[0].strip().rstrip('>').strip()
            
            # Extract message content
            content_start = agent_msg.find(">") + 1
            content_end = agent_msg.rfind("<")
            message_content = agent_msg[content_start:content_end].strip()
            
            # Check if agent is messaging itself (parse message for @ mentions or other indicators)
            if message_content.startswith(f"@{agent_name}") or message_content.startswith(f"{agent_name},"):
                raise ValueError(f"Agent '{agent_name}' cannot message itself")
            
            ai_agent_actions.append(
                AIAgentAction(message=message_content, recipient=agent_name)
            )
            
            # Find the next agent_message tag
            agent_msg_start = response.find("<agent_message", agent_msg_end)

        # Validate that agents aren't sending messages to themselves
        for action in ai_agent_actions:
            if action.message.startswith(f"@{action.recipient}"):
                raise ValueError(f"Agent '{action.recipient}' cannot message itself")

        return Actions(user_actions=user_actions, ai_agent_actions=ai_agent_actions)

    async def _generate(self, prompt_text: str) -> Actions:
        max_attempts = 3
        current_attempt = 0
        last_error = None
        
        while current_attempt < max_attempts:
            current_attempt += 1
            try:
                # Add error message to prompt if this is a retry
                current_prompt = prompt_text
                if last_error:
                    current_prompt = f"{prompt_text}\n\nError in previous response: {last_error}. Please fix and try again."
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": self.result_format_prompt + current_prompt}]
                )
                
                response_text = response.choices[0].message.content
                return self.parse_response(response_text)
            
            except ValueError as e:
                last_error = str(e)
                if current_attempt >= max_attempts:
                    raise ValueError(f"Failed after {max_attempts} attempts. Last error: {last_error}")
        
        # This should never be reached due to the exception above, but just in case
        raise ValueError(f"Failed to generate a valid response after {max_attempts} attempts")
