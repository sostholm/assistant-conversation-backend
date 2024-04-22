from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import tool

class MemoryInput(BaseModel):
    """Input for the short-term memory tool."""
    item: str = Field(description="A string of text that is to be put/removed in short-term memory.")
    action: str = Field(default="put", description="The action to perform on the item. Options: 'get', 'put', 'remove'. get will return the current memory. put will add the item to the memory. remove will remove the item from the memory.")

@tool("memory-tool", args_schema=MemoryInput)
def memory_tool(item: str, action: str) -> str:
    """stores strings of text in memory. Each entry will be separated by a newline character. The memory is stored in the global variable MEMORY and is added to the system message between <MEMORY></MEMORY>."""

    # Create file if it doesn't exist

    try:
        with open("memory.txt", "r") as f:
            MEMORY = f.read()
    except FileNotFoundError:
        with open("memory.txt", "w") as f:
            f.write("")
            MEMORY = ""

    if action == "put":
        MEMORY = MEMORY + item + "\n"
    
    elif action == "remove":
        MEMORY = MEMORY.replace(item + "\n", "")

    # write to file
    with open("memory.txt", "w") as f:
        f.write(MEMORY)
    
    return MEMORY