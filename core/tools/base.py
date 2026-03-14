from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    Abstract Base Class for all tools the Agent can use.
    Tools must define a name and description to be injected into the LLM context.
    """
    name: str = ""
    description: str = ""
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        The core execution logic of the tool. 
        Implementations should handle internal errors gracefully.
        """
        pass
        
    def to_schema(self) -> dict:
        """
        Returns a JSON schema description of the tool.
        This is injected into the prompt so the LLM knows how to call it.
        """
        return {
            "name": self.name,
            "description": self.description,
        }
