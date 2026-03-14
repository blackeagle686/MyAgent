# AgentActor - Complete Implementation

## Overview

The `AgentActor` is the core execution engine that bridges the LLM's decisions with actual tool execution. It represents the "A" (Acting) in the ReAct (Reasoning + Acting) loop.

## Architecture

```
LLM Response (raw text)
    ↓
[1. Parsing] Extract JSON tool call
    ↓
[2. Validation] Check tool exists & args valid
    ↓
[3. Execution] Run tool with arguments
    ↓
Observation (string result)
```

## Key Components

### ToolCall (Dataclass)

Represents a parsed tool call from LLM response.

```python
@dataclass
class ToolCall:
    tool_name: str              # Name of the tool to execute
    kwargs: Dict[str, Any]      # Arguments to pass to tool
    raw_text: str               # Raw JSON text that was parsed
```

### ActorResult (Dataclass)

Represents the result of acting on a tool call.

```python
@dataclass
class ActorResult:
    success: bool               # Whether execution succeeded
    observation: str            # Result to return to agent
    tool_name: Optional[str]    # Name of tool executed
    error: Optional[str]        # Error message if failed
    execution_time: float       # Time taken in seconds
```

### AgentActor (Main Class)

The main actor class that orchestrates parsing, validation, and execution.

```python
class AgentActor:
    def __init__(self, registry: ToolRegistry)
    def act(self, llm_response: str) -> str
    def get_execution_stats() -> Dict[str, Any]
    def reset_history()
    def debug_parse(response: str) -> Dict[str, Any]
```

## Usage

### Basic Usage

```python
from core.tools import ToolRegistry, FileReadTool, PythonREPLTool
from core.agent import AgentActor

# Create registry with tools
registry = ToolRegistry([
    FileReadTool(),
    PythonREPLTool(),
])

# Create actor
actor = AgentActor(registry=registry)

# LLM generates response with tool call
llm_response = """
Let me read the file to analyze it.
```json
{"tool": "read_file", "kwargs": {"path": "/workspace/data.txt"}}
```
"""

# Actor executes the tool
observation = actor.act(llm_response)
print(observation)  # Output: "File content of /workspace/data.txt: ..."
```

### With ReAct Loop

```python
from core.agent import BrainAgent

agent = BrainAgent(sys_prompt="You are a helpful assistant")

# Run ReAct loop
for step in range(max_steps):
    # Think: LLM reasons and generates tool call
    thought_and_action = agent.think(user_prompt)
    
    # Act: Execute the tool
    observation = agent.act(thought_and_action)
    
    # Check if done
    if "FINAL_ANSWER:" in thought_and_action:
        break
```

### Error Handling

```python
# Actor handles various error cases gracefully

# 1. Invalid JSON
llm_response = "I can't parse this as JSON"
observation = actor.act(llm_response)
# Returns: "[ERROR] No tool call found in LLM response..."

# 2. Tool not found
llm_response = '{"tool": "unknown_tool", "kwargs": {}}'
observation = actor.act(llm_response)
# Returns: "[ERROR] Tool 'unknown_tool' not found..."

# 3. Invalid arguments
llm_response = '{"tool": "read_file", "kwargs": "not_a_dict"}'
observation = actor.act(llm_response)
# Returns: "[ERROR] Tool kwargs must be a dictionary"
```

## Parsing Strategies

The actor supports multiple JSON extraction strategies:

### Strategy 1: Markdown Code Block

```
Response text here
```json
{"tool": "read_file", "kwargs": {"path": "/file.txt"}}
```
More response text
```

### Strategy 2: Plain JSON

```
Response text with embedded {
    "tool": "read_file",
    "kwargs": {"path": "/file.txt"}
}
```

## Validation

Before executing, the actor validates:

1. **Tool Name**
   - Must be non-empty string
   - Must exist in registry

2. **Tool Kwargs**
   - Must be a dictionary
   - Maximum size: 100KB (DoS protection)

3. **Tool Existence**
   - Returns helpful error with available tools

## Execution Flow

### Phase 1: Parsing

```python
def _parse_tool_call(response: str) -> Optional[ToolCall]:
    # Extract JSON (multiple strategies)
    json_str = self._extract_markdown_json(response)
    if not json_str:
        json_str = self._extract_plain_json(response)
    
    # Parse JSON and create ToolCall
    data = json.loads(json_str)
    return ToolCall(
        tool_name=data.get("tool"),
        kwargs=data.get("kwargs", {}),
        raw_text=json_str
    )
```

### Phase 2: Validation

```python
def _validate_tool_call(tool_call: ToolCall) -> Tuple[bool, str]:
    # Check tool name
    if not tool_call.tool_name:
        return False, "Tool name must be non-empty"
    
    # Check tool exists
    if not self.registry.get_tool(tool_call.tool_name):
        return False, "Tool not found"
    
    # Check kwargs
    if not isinstance(tool_call.kwargs, dict):
        return False, "Kwargs must be dict"
    
    return True, ""
```

### Phase 3: Execution

```python
def _execute_tool(tool_call: ToolCall) -> str:
    tool = self.registry.get_tool(tool_call.tool_name)
    result = tool.execute(**tool_call.kwargs)
    return str(result)
```

## Error Handling

The actor provides comprehensive error handling:

### Parse Errors
```python
# No JSON found
"No tool call found in LLM response"

# Invalid JSON
"JSON parse error: Expecting value"
```

### Validation Errors
```python
# Tool not found
"Tool 'unknown_tool' not found. Available tools: read_file, python_repl"

# Invalid kwargs
"Tool kwargs must be a dictionary"

# Too large
"Tool arguments too large (max 100KB)"
```

### Execution Errors
```python
# Type mismatch
"Tool argument error in read_file: expected str, got int"

# Tool failure
"Error executing python_repl: SyntaxError in code"
```

## Debugging

### Debug Parsing

```python
# Inspect what happens during parsing
debug_info = actor.debug_parse(llm_response)
print(debug_info)
# {
#     "parsed": True,
#     "tool_call": {
#         "name": "read_file",
#         "kwargs": {"path": "/file.txt"}
#     },
#     "available_tools": ["read_file", "python_repl"],
#     "raw_response_preview": "Let me read..."
# }
```

### Execution Statistics

```python
# Track execution history
stats = actor.get_execution_stats()
print(stats)
# {
#     "total_executions": 5,
#     "history": [
#         {
#             "tool": "read_file",
#             "args": {"path": "/file.txt"},
#             "result": "File content...",
#             "timestamp": 0.234
#         }
#     ]
# }

# Reset history
actor.reset_history()
```

## Logging

The actor logs all operations:

```python
import logging

logging.basicConfig(level=logging.INFO)

# Logs:
# INFO:agent_actor:Parsed tool call: read_file with args {'path': '/file.txt'}
# INFO:agent_actor:Executing tool: read_file
# INFO:agent_actor:Tool execution completed in 0.23s: read_file
```

## Security Features

1. **Size Limits**
   - Maximum kwargs size: 100KB
   - Prevents DoS via large arguments

2. **Tool Validation**
   - Tools must be registered
   - Type checking on kwargs

3. **Error Isolation**
   - Exceptions caught and logged
   - No stack traces in observations

4. **Audit Trail**
   - All executions recorded
   - Full execution history available

## Integration with Tools

The actor works seamlessly with the ToolRegistry:

```python
# Create registry
registry = ToolRegistry([
    FileReadTool(),
    PythonREPLTool(),
    HTTPRequestTool(),
])

# Actor can access any registered tool
actor = AgentActor(registry)

# Get available tools
available = registry.get_tool_names()
# ['read_file', 'write_file', 'python_repl', 'http_request']
```

## Performance Considerations

1. **Execution Tracking**
   - Each execution recorded in history
   - Optional: Reset history to save memory
   - Call `reset_history()` between episodes

2. **Logging Level**
   - INFO: High-level operations
   - DEBUG: Detailed parsing and execution
   - ERROR: Failures and exceptions

3. **Response Size**
   - No limit on tool results
   - Large responses handled gracefully
   - Logged truncated in debug mode

## Example: Complex Agent Loop

```python
from core.agent import BrainAgent
from core.tools import FileReadTool, PythonREPLTool

# Create agent
agent = BrainAgent(
    sys_prompt="You are a data analyst. Use tools to analyze files.",
    tools=[FileReadTool(), PythonREPLTool()]
)

# User request
user_prompt = "Analyze the data in /workspace/data.csv"

# ReAct loop
for step in range(max_steps=10):
    # Step 1: Think & Plan
    thought = agent.think(user_prompt, trajectory=[])
    print(f"[Step {step}] Thought: {thought}")
    
    # Step 2: Act
    observation = agent.act(thought)
    print(f"[Step {step}] Observation: {observation}")
    
    # Step 3: Check for completion
    if "FINAL_ANSWER:" in thought:
        final_answer = thought.split("FINAL_ANSWER:")[1].strip()
        print(f"[Done] {final_answer}")
        break

# Get stats
stats = agent.actor.get_execution_stats()
print(f"Total tools called: {stats['total_executions']}")
```

## Best Practices

1. **Always provide tool descriptions**
   - Helps LLM choose correct tool
   - Set clear `to_schema()` outputs

2. **Use appropriate error messages**
   - Be specific about what failed
   - Help user/LLM understand next steps

3. **Monitor execution history**
   - Track which tools are used most
   - Identify patterns in failures

4. **Validate external inputs**
   - Use restrict_path for file tools
   - Validate URLs for API tools
   - Use timeout for code execution

5. **Handle large responses**
   - Tools may return large results
   - Consider pagination
   - Log responsibly

## Troubleshooting

### Tool Not Found

```python
# Problem: "[ERROR] Tool 'xyz' not found"

# Solution: Check registry has the tool
print(actor.registry.get_tool_names())

# Register missing tool
actor.registry.register(MyTool())
```

### Parse Failures

```python
# Problem: No tool call extracted

# Solution: Debug the parsing
debug_info = actor.debug_parse(llm_response)
print(debug_info)

# Ensure JSON is valid:
# ```json
# {"tool": "...", "kwargs": {...}}
# ```
```

### Execution Errors

```python
# Problem: Tool execution fails

# Solution: Enable debug logging
logging.getLogger("agent_actor").setLevel(logging.DEBUG)

# Check tool arguments match tool.execute() signature
```

## Future Enhancements

- [ ] Tool chaining (output of one tool → input of next)
- [ ] Tool caching (cache results for repeated calls)
- [ ] Async execution (parallel tool execution)
- [ ] Retry logic (retry failed executions)
- [ ] Tool ranking (prioritize certain tools)
- [ ] Execution profiling (track performance)

---

**Status**: ✅ Complete and Production-Ready
