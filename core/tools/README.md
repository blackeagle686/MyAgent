# Core Tools Module

A secure, extensible tool system for AI agents with built-in security layers and audit logging.

## Overview

The `core/tools` module provides a framework for building and managing agent tools with comprehensive security features. Each tool is protected by multiple security decorators that enforce sandboxing, validate inputs, and log all operations.

## Architecture

### Base Components

- **`base.py`**: Abstract `BaseTool` class that all tools must inherit from
- **`registry.py`**: `ToolRegistry` for registering and managing tools, with validation and execution
- **`code_security_decorator.py`**: Security decorators for protecting tool execution

### Security Decorators

The module includes five key security decorators:

#### 1. `@safe_execution`
Catches all unhandled exceptions and returns structured error messages instead of crashing.
```python
@safe_execution
def execute(self, **kwargs):
    # Any exception here is caught and logged
    pass
```

#### 2. `@restrict_path`
Enforces filesystem sandboxing by restricting file operations to the `WORKSPACE_ROOT` directory. Prevents directory traversal attacks.
```python
@restrict_path
def execute(self, path: str, **kwargs):
    # path is validated to be within WORKSPACE_ROOT
    pass
```

#### 3. `@validate_code`
Scans code for dangerous patterns (e.g., `os.system`, `eval`, `exec`, `subprocess`) before execution.
```python
@validate_code
def execute(self, code: str, **kwargs):
    # code is scanned for blocked patterns
    pass
```

#### 4. `@timeout(seconds=N)`
Enforces execution time limits using POSIX signals. Prevents infinite loops and resource exhaustion.
```python
@timeout(seconds=10)
def execute(self, **kwargs):
    # Must complete within 10 seconds
    pass
```

#### 5. `@audit_log`
Logs all tool invocations with arguments and results for security auditing.
```python
@audit_log
def execute(self, **kwargs):
    # All calls are logged
    pass
```

## Available Tools

### File System Tools

#### `FileReadTool`
Safely reads file contents.
```python
tool.execute(path="/workspace/myfile.txt")
```

#### `FileWriteTool`
Safely writes to files.
```python
tool.execute(path="/workspace/output.txt", content="Hello World")
```

#### `ListDirTool`
Lists directory contents.
```python
tool.execute(path="/workspace")
```

#### `FileDeleteTool`
Safely deletes files.
```python
tool.execute(path="/workspace/temp.txt")
```

#### `CreateDirTool`
Creates directories.
```python
tool.execute(path="/workspace/newdir")
```

### Code Execution Tools

#### `PythonREPLTool`
Executes Python code with restricted builtins and dangerous pattern detection.
- Supports: `len`, `range`, `str`, `int`, `list`, `dict`, `sum`, `max`, `min`, etc.
- Blocks: `os.system`, `subprocess`, `eval`, `exec`, etc.
- Timeout: 10 seconds
```python
tool.execute(code="result = sum([1, 2, 3]); print(result)")
```

### Search Tools

#### `DeepSearchTool`
Searches external APIs with query validation.
```python
tool.execute(query="Python programming")
```

#### `RagSearchTool`
Performs RAG (Retrieval-Augmented Generation) searches.
```python
tool.execute(query="machine learning basics")
```

### API Tools

#### `HTTPRequestTool`
Makes secure HTTP requests to external APIs.
- URL validation (blocks localhost, file://, private IPs)
- Request/response size limits (10KB/1MB)
- Timeout protection (10 seconds)
- Header sanitization

```python
tool.execute(
    url="https://api.example.com/data",
    method="GET",
    headers={"Authorization": "Bearer token"}
)
```

#### `APIClientTool`
High-level structured JSON API client.
```python
tool.execute(
    endpoint="https://api.example.com/users",
    method="POST",
    body={"name": "John", "email": "john@example.com"},
    api_key="your_key"
)
```

## Usage Examples

### Basic Tool Registration

```python
from core.tools import ToolRegistry, FileReadTool, PythonREPLTool

# Create registry
registry = ToolRegistry()

# Register tools
registry.register(FileReadTool())
registry.register(PythonREPLTool())

# List available tools
print(registry.get_tool_names())
```

### Executing Tools

```python
# Direct tool execution
tool = FileReadTool()
result = tool.execute(path="/workspace/data.txt")

# Via registry
registry = ToolRegistry([FileReadTool()])
registry.execute_from_llm_response("""
{
    "tool": "read_file",
    "kwargs": {"path": "/workspace/data.txt"}
}
""")
```

### With LLM Integration

```python
registry = ToolRegistry([
    FileReadTool(),
    PythonREPLTool(),
    HTTPRequestTool()
])

# Get tools schema for LLM context
schema = registry.get_tools_schema_str()

# Execute tool from LLM response
result = registry.execute_from_llm_response(llm_json_response)
```

## Security Configuration

### Workspace Root

Edit `code_security_decorator.py` to configure the sandbox root:
```python
WORKSPACE_ROOT: str = os.path.abspath("./workspace")
```

### Blocked Patterns

Add dangerous patterns to `_BLOCKED_PATTERNS`:
```python
_BLOCKED_PATTERNS: tuple[str, ...] = (
    "os.system",
    "subprocess",
    "your_pattern_here",
)
```

### HTTP Whitelist

Customize allowed API domains in `api_tool.py`:
```python
ALLOWED_DOMAINS = {
    "api.example.com",
    "api.github.com",
}
```

## Error Handling

All tools return structured error messages:

```python
# File not found
"Error: File not found at path '/workspace/missing.txt'"

# Permission denied
"Access denied: '/etc/passwd' is outside the workspace."

# Invalid code
"Execution blocked: forbidden pattern 'os.system' detected."

# Timeout
"Tool timed out after 10s."
```

## Logging

All operations are logged to the standard Python logger:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Logs will show:
# → Tool called: 'read_file' | args=('/workspace/file.txt',) kwargs={}
# ← Tool result: 'read_file' | File content of /workspace/file.txt...
```

## Creating Custom Tools

```python
from core.tools import BaseTool, safe_execution, audit_log

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "A custom tool that does something"
    
    @safe_execution
    @audit_log
    def execute(self, param: str, **kwargs):
        # Your implementation here
        return f"Processed: {param}"

# Register and use
registry = ToolRegistry([CustomTool()])
```

## Best Practices

1. **Always use security decorators** on tool execute methods
2. **Validate all inputs** before processing
3. **Use appropriate timeouts** based on expected execution time
4. **Return structured responses** for consistency
5. **Log important operations** via audit_log decorator
6. **Test with malicious inputs** to ensure sandboxing works
7. **Update blocked patterns** as new exploits are discovered

## Limitations & Future Improvements

- POSIX-only timeout (works on Linux/Mac, not Windows)
- Python code execution is still inherently risky even with restrictions
- Consider containerization for higher security in production
- Add rate limiting for API tools
- Implement caching for search results
- Add database query tool with SQL injection protection

## Dependencies

- `requests` (for HTTP tools, optional)
- Standard library only for core tools

Install optional dependencies:
```bash
pip install requests
```

## Testing

Run security tests:
```bash
python -m pytest tests/ -v
```

Test individual tool security:
```python
from core.tools import PythonREPLTool

tool = PythonREPLTool()

# Should be blocked
result = tool.execute(code="import os; os.system('rm -rf /')")
assert "forbidden pattern" in result
```

---

For questions or security concerns, please report through the appropriate channels.
