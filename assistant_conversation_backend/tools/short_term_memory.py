from typing import Dict, List, Optional, Type, Union

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from pymongo import MongoClient



# Connect to your MongoDB database
client = MongoClient('mongodb://192.168.0.218:27017/')
db = client['assistant_conversation']  # replace with your database name
memory_collection = db['memory']  # replace with your collection name

class MemoryInput(BaseModel):
    """Input for the short-term memory tool."""
    item: str = Field(description="A string of text that is to be put/removed in short-term memory.")
    action: str = Field(default="put", description="The action to perform on the item. Options: 'get', 'put', 'remove'.")


class ShortTermMemory(BaseTool):
    """Tool for managing short-term memory, which is useful for storing and retrieving information quickly."""
    
    name: str = "short_term_memory"
    description: str = (
        "A tool that allows for the management of short-term memory. The contents of the short term memory is between <memory></memory>. "
    )
    args_schema: Type[BaseModel] = MemoryInput


    def _run(
        self,
        item: str,
        action: str = "put",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Union[List[Dict], str]:
        """Use the tool."""

        # Create a new document to insert into the collection if it doesn't exist
        new_document = {
            "memory": ""
        }
        memory_document = memory_collection.find_one(new_document)
        if memory_document is None:
            result = memory_collection.insert_one(new_document)
            memory_document = memory_collection.find_one({'_id': result.inserted_id})

        try:
            if action == "put":
                memory_collection.update_one(
                    {'_id': memory_document['_id']},
                    {"$set": {"memory": memory_document["memory"] + item + "\n"}}
                )
            elif action == "remove":
                memory_collection.update_one(
                    {'_id': memory_document['_id']},
                    {"$set": {"memory": memory_document["memory"].replace(item + "\n", "")}}
                )
            return memory_document["memory"]
        except Exception as e:
            return repr(e)

    async def _arun(
        self,
        item: str,
        action: str = "put",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Union[List[Dict], str]:
        """Use the tool asynchronously."""
        try:
            if action == "put":
                self.MEMORY = self.MEMORY + item
            elif action == "remove":
                self.MEMORY = self.MEMORY.replace(item, "")
            return self.MEMORY
        except Exception as e:
            return repr(e)