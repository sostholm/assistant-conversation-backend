from openai import AsyncOpenAI
import os
from .base_model import BaseAIModel
from .output_parsing import parse_llm_output_to_actions, Actions, ParsingError
import re


class LocalModel(BaseAIModel):
    def __init__(self, model_name: str = "qwen-qwq-32b"): # Removed known_agent_names from init
        # Removed self.result_format_prompt initialization
        self.model = model_name
        self.client = AsyncOpenAI(
            base_url="http://127.0.0.1:1234/v1",
            # api_key=os.environ["GROQ_API_KEY"],
        )
        # Removed self.known_agent_names initialization

    # Updated signature to accept instructions, message, and known_agent_names
    async def _generate(self, instructions: str, message: str, known_agent_names: set[str]) -> Actions:
        max_attempts = 3
        current_attempt = 0
        last_error = None

        while current_attempt < max_attempts:
            current_attempt += 1
            try:
                # Construct messages list
                messages_for_api = []
                messages_for_api.append({"role": "system", "content": instructions})

                if last_error:
                    # Add error context as a preceding user message in retries
                    error_context = (
                        f"The previous attempt failed with this error: {last_error}\n"
                        f"Please ensure your response strictly follows the required format."
                    )
                    messages_for_api.append({"role": "user", "content": error_context})

                # Add the main user message
                messages_for_api.append({"role": "user", "content": message})

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages_for_api # Pass the constructed messages list
                )

                response_text = response.choices[0].message.content

                # Preprocess the response text
                # 1. Remove leading/trailing whitespace
                processed_text = response_text.strip()
                # 2. Remove <think>...</think> block if it exists at the beginning
                # Use re.DOTALL to make '.' match newlines within the think block
                processed_text = re.sub(r"^\s*<think>.*?</think>\s*", "", processed_text, flags=re.DOTALL)

                # Use the new parsing function, passing known_agent_names from args
                # and the processed text
                return parse_llm_output_to_actions(processed_text, known_agent_names)

            except ParsingError as e:
                last_error = str(e)
                # Include raw and processed text in error for debugging
                print(f"Attempt {current_attempt} failed parsing. Raw response:\n---\n{response_text}\n---\nProcessed text:\n---\n{processed_text}\n---\nError: {e}")
                if current_attempt >= max_attempts:
                    raise ParsingError(f"Failed after {max_attempts} attempts. Last error: {last_error}")

        # This should ideally not be reached if exceptions are handled correctly
        raise RuntimeError(f"Failed to generate a valid response after {max_attempts} attempts. Last error: {last_error}")
