from typing import Any
from .base import BaseTool
from ..services.llm_service import client

class FastAnswerTool(BaseTool):
    """
    A tool to provide fast, direct answers for simple or factual queries 
    that don't require external search or RAG.
    """
    name = "fast_answer"
    description = (
        "Provides a direct answer to simple questions using general knowledge. "
        "Use this for basic facts, definitions, or simple reasoning tasks. "
        "Provide 'query' argument."
    )
    
    def execute(self, query: str, **kwargs) -> Any:
        if not query or not isinstance(query, str):
            return "Error: 'query' must be a non-empty string."
        
        try:
            # Use a slightly higher temperature for conversational answers if needed
            # but keep it low for factual consistency as per current architecture
            response = client.generate(
                user_prompt=f"Please provide a direct and concise answer to: {query}",
                sys_prompt="You are a helpful assistant providing fast and accurate answers."
            )
            return response
        except Exception as e:
            return f"FastAnswer failed: {str(e)}"
