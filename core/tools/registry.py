import json
import logging
from typing import Dict, List, Type, Any
from .base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Manages parsing and executing tool commands from the LLM with security validation."""
    
    def __init__(self, tools: List[BaseTool] = None):
        self._tools: Dict[str, BaseTool] = {}
        if tools:
            for tool in tools:
                self.register(tool)
                
    def register(self, tool: BaseTool):
        """Register a new tool instance with validation."""
        if not isinstance(tool, BaseTool):
            logger.error(f"Invalid tool: {tool} does not inherit from BaseTool")
            raise TypeError(f"Tool must inherit from BaseTool, got {type(tool)}")
        
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} is already registered. Overwriting.")
        
        self._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")
        
    def get_tool(self, name: str) -> BaseTool:
        """Retrieve a tool by name."""
        return self._tools.get(name)
        
    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())
        
    def get_tools_schema_str(self) -> str:
        """Returns a string representation of all tools for the LLM prompt."""
        schemas = []
        for tool in self._tools.values():
            try:
                schema = tool.to_schema()
                schemas.append(str(schema))
            except Exception as e:
                logger.error(f"Failed to generate schema for tool {tool.name}: {e}")
        return "\n".join(schemas)
        
    def validate_tool_call(self, command: dict) -> tuple[bool, str]:
        """
        Validate a tool call command before execution.
        Returns (is_valid, error_message)
        """
        if not isinstance(command, dict):
            return False, "Tool command must be a dictionary"
        
        tool_name = command.get("tool")
        if not tool_name:
            return False, "No 'tool' key found in command"
        
        if tool_name not in self._tools:
            available = list(self._tools.keys())
            return False, f"Tool '{tool_name}' not found. Available tools: {available}"
        
        kwargs = command.get("kwargs", {})
        if not isinstance(kwargs, dict):
            return False, "'kwargs' must be a dictionary"
        
        return True, ""
        
    def execute_from_llm_response(self, llm_response: str) -> str:
        """
        Parses the LLM response for a tool call (JSON format), 
        validates it, executes it, and returns the observation as a string.
        """
        try:
            # Extract JSON from response
            command = self._extract_json(llm_response)
            if not command:
                return "Error: No valid JSON tool call found in response."
            
            # Validate tool call
            is_valid, error_msg = self.validate_tool_call(command)
            if not is_valid:
                logger.warning(f"Invalid tool call: {error_msg}")
                return f"Error: {error_msg}"
            
            tool_name = command.get("tool")
            kwargs = command.get("kwargs", {})
            
            tool = self.get_tool(tool_name)
            logger.info(f"Executing tool '{tool_name}' with args {kwargs}")
            
            result = tool.execute(**kwargs)
            logger.info(f"Tool '{tool_name}' execution completed")
            
            return str(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return f"Error: Could not parse JSON tool call: {e}"
        except Exception as e:
            logger.error(f"Unexpected error executing tool: {e}")
            return f"Error executing tool: {e}"
    
    def _extract_json(self, response: str) -> dict:
        """Extract JSON object from LLM response."""
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        elif "{" in response and "}" in response:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            return json.loads(json_str)
        return None

