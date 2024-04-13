from typing import Dict, List, Optional, Type, Union

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from pymongo import MongoClient

class NewsAPIInput(BaseModel):
    """Input for the news fetching tool."""
    query: str = Field(description="Search query to look up news articles.")
    recency: str = Field(default="24h", description="Filter results by recency. Examples: '24h' for the last 24 hours, '7d' for the last 7 days, etc.")


class RecentNewsSearch(BaseTool):
    """Tool that queries a news API for recent articles, focusing on delivering fresh and relevant information."""
    
    name: str = "recent_news_search"
    description: str = (
        "A tool optimized for fetching recent news articles based on a search query. "
        "It's useful for staying updated with the latest news and current events. "
        "Input should be a search query and an optional recency filter."
    )
    max_results: int = 10
    args_schema: Type[BaseModel] = NewsAPIInput

    def _run(
        self,
        query: str,
        recency: str = "24h",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Union[List[Dict], str]:
        """Use the tool."""
        try:
            # Adjust the method call based on the actual API's functionality
            return self.api_wrapper.fetch_recent_news(
                query=query,
                max_results=self.max_results,
                recency=recency,
            )
        except Exception as e:
            return repr(e)

    async def _arun(
        self,
        query: str,
        recency: str = "24h",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Union[List[Dict], str]:
        """Use the tool asynchronously."""
        try:
            # Adjust the method call based on the actual API's functionality
            return await self.api_wrapper.fetch_recent_news_async(
                query=query,
                max_results=self.max_results,
                recency=recency,
            )
        except Exception as e:
            return repr(e)