"""
Agent Actor Module
==================
Responsible for parsing LLM responses and executing tool commands.

The Actor:
    1. Parses JSON tool calls from LLM responses
    2. Validates tool existence and arguments
    3. Executes tools with error handling
    4. Transforms results into observations for the agent loop
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a parsed tool call from LLM response."""
    tool_name: str
    kwargs: Dict[str, Any]
    raw_text: str
    
    def is_valid(self) -> bool:
        """Check if tool call has required fields."""
        return bool(self.tool_name) and isinstance(self.kwargs, dict)


@dataclass
class ActorResult:
    """Result of agent acting on a tool call."""
    success: bool
    observation: str
    tool_name: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class AgentActor:
    """
    Executes tool commands extracted from LLM responses.
    
    The Actor is responsible for the "A" in ReAct (Reasoning + Acting).
    It bridges between the LLM's natural language thinking and actual tool execution.
    """
    
    def __init__(self, registry: ToolRegistry):
        """
        Initialize the actor with a tool registry.
        
        Args:
            registry: ToolRegistry containing all available tools
        """
        self.registry = registry
        self._execution_count = 0
        self._execution_history = []
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def act(self, llm_response: str) -> str:
        """
        Parse and execute a tool call from LLM response.
        
        This is the main entry point for the agent loop. It:
        1. Extracts JSON tool call from LLM response
        2. Validates the tool call
        3. Executes the tool
        4. Returns the observation
        
        Args:
            llm_response: Raw response from LLM containing tool call
            
        Returns:
            Observation string (tool result or error message)
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: Parse tool call
            tool_call = self._parse_tool_call(llm_response)
            if not tool_call:
                return self._format_error(
                    "No tool call found in LLM response. "
                    "Expected JSON block with 'tool' and 'kwargs' keys."
                )
            
            logger.info(f"Parsed tool call: {tool_call.tool_name} with args {tool_call.kwargs}")
            
            # Step 2: Validate tool call
            is_valid, error_msg = self._validate_tool_call(tool_call)
            if not is_valid:
                return self._format_error(error_msg)
            
            # Step 3: Execute tool
            observation = self._execute_tool(tool_call)
            
            # Record execution
            execution_time = time.time() - start_time
            self._execution_count += 1
            self._execution_history.append({
                "tool": tool_call.tool_name,
                "args": tool_call.kwargs,
                "result": observation,
                "timestamp": execution_time
            })
            
            logger.info(f"Tool execution completed in {execution_time:.2f}s: {tool_call.tool_name}")
            return observation
            
        except Exception as e:
            logger.error(f"Unexpected error in actor: {e}", exc_info=True)
            return self._format_error(f"Unexpected error: {str(e)}")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get statistics about tool executions."""
        return {
            "total_executions": self._execution_count,
            "history": self._execution_history,
        }
    
    def reset_history(self):
        """Clear execution history."""
        self._execution_history = []
        self._execution_count = 0
    
    # =========================================================================
    # Private: Parsing
    # =========================================================================
    
    def _parse_tool_call(self, response: str) -> Optional[ToolCall]:
        """
        Extract and parse a JSON tool call from LLM response.
        
        Tries multiple extraction strategies:
        1. Markdown code block: ```json {...} ```
        2. Plain JSON block: {...}
        
        Args:
            response: Raw LLM response text
            
        Returns:
            ToolCall object or None if parsing fails
        """
        if not response or not isinstance(response, str):
            logger.warning("Invalid response format")
            return None
        
        # Strategy 1: Markdown code block
        json_str = self._extract_markdown_json(response)
        
        # Strategy 2: Plain JSON block
        if not json_str:
            json_str = self._extract_plain_json(response)
        
        if not json_str:
            logger.debug("Could not extract JSON from response")
            return None
        
        # Parse JSON
        try:
            data = json.loads(json_str)
            
            tool_call = ToolCall(
                tool_name=data.get("tool", ""),
                kwargs=data.get("kwargs", {}),
                raw_text=json_str
            )
            
            if tool_call.is_valid():
                return tool_call
            else:
                logger.warning(f"Invalid tool call structure: {data}")
                return None
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return None
    
    def _extract_markdown_json(self, text: str) -> Optional[str]:
        """Extract JSON from ```json...``` block."""
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_plain_json(self, text: str) -> Optional[str]:
        """Extract JSON object from plain text."""
        # Find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
        return None
    
    # =========================================================================
    # Private: Validation
    # =========================================================================
    
    def _validate_tool_call(self, tool_call: ToolCall) -> Tuple[bool, str]:
        """
        Validate a parsed tool call.
        
        Checks:
        1. Tool name is not empty
        2. Tool exists in registry
        3. Kwargs is a dictionary
        4. Kwargs are reasonable (not too large)
        
        Args:
            tool_call: Parsed ToolCall object
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check tool name
        if not tool_call.tool_name or not isinstance(tool_call.tool_name, str):
            return False, "Tool name must be a non-empty string"
        
        # Check tool exists
        tool = self.registry.get_tool(tool_call.tool_name)
        if not tool:
            available_tools = ", ".join(self.registry.get_tool_names())
            return False, (
                f"Tool '{tool_call.tool_name}' not found. "
                f"Available tools: {available_tools}"
            )
        
        # Check kwargs
        if not isinstance(tool_call.kwargs, dict):
            return False, "Tool kwargs must be a dictionary"
        
        # Check kwargs size (prevent DoS)
        kwargs_str = json.dumps(tool_call.kwargs)
        if len(kwargs_str) > 100000:  # 100KB limit
            return False, "Tool arguments too large (max 100KB)"
        
        return True, ""
    
    # =========================================================================
    # Private: Execution
    # =========================================================================
    
    def _execute_tool(self, tool_call: ToolCall) -> str:
        """
        Execute a tool with the given arguments.
        
        Args:
            tool_call: Parsed and validated ToolCall
            
        Returns:
            String observation from tool execution
        """
        try:
            tool = self.registry.get_tool(tool_call.tool_name)
            
            logger.info(f"Executing tool: {tool_call.tool_name}")
            logger.debug(f"Arguments: {tool_call.kwargs}")
            
            # Execute tool
            result = tool.execute(**tool_call.kwargs)
            
            # Convert result to string
            observation = str(result)
            
            logger.debug(f"Tool result: {observation[:200]}...")  # Log first 200 chars
            
            return observation
            
        except TypeError as e:
            error_msg = f"Tool argument error in {tool_call.tool_name}: {str(e)}"
            logger.error(error_msg)
            return self._format_error(error_msg)
        except Exception as e:
            error_msg = f"Error executing {tool_call.tool_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._format_error(error_msg)
    
    # =========================================================================
    # Private: Formatting
    # =========================================================================
    
    def _format_error(self, error_msg: str) -> str:
        """Format an error message as an observation."""
        return f"[ERROR] {error_msg}"
    
    def _format_result(self, result: str, tool_name: str) -> str:
        """Format a successful tool result."""
        return f"[{tool_name}] {result}"
    
    # =========================================================================
    # Debugging & Introspection
    # =========================================================================
    
    def debug_parse(self, response: str) -> Dict[str, Any]:
        """
        Debug helper: Parse response and show all details.
        
        Useful for understanding why a tool call might fail.
        """
        tool_call = self._parse_tool_call(response)
        
        return {
            "parsed": tool_call is not None,
            "tool_call": {
                "name": tool_call.tool_name if tool_call else None,
                "kwargs": tool_call.kwargs if tool_call else None,
            } if tool_call else None,
            "available_tools": self.registry.get_tool_names(),
            "raw_response_preview": response[:200] + "..." if len(response) > 200 else response,
        }
