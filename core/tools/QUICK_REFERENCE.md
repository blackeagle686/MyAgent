# Core Tools - Quick Reference Guide

## 📚 Quick Start

### Import All Tools
```python
from core.tools import (
    # Base
    BaseTool, ToolRegistry,
    # File tools
    FileReadTool, FileWriteTool, ListDirTool, FileDeleteTool, CreateDirTool,
    # Code tools
    PythonREPLTool,
    # Search tools
    DeepSearchTool, RagSearchTool,
    # API tools
    HTTPRequestTool, APIClientTool,
    # Security
    safe_execution, restrict_path, validate_code, timeout, audit_log,
)
```

### Setup Registry
```python
registry = ToolRegistry()
registry.register(FileReadTool())
registry.register(PythonREPLTool())
registry.register(HTTPRequestTool())
```

---

## 🛠️ Tool Cheat Sheet

### File Operations
```python
# Read
FileReadTool().execute(path="/workspace/file.txt")

# Write
FileWriteTool().execute(path="/workspace/out.txt", content="hello")

# List
ListDirTool().execute(path="/workspace")

# Delete
FileDeleteTool().execute(path="/workspace/temp.txt")

# Create Dir
CreateDirTool().execute(path="/workspace/newdir")
```

### Code Execution
```python
# Python
PythonREPLTool().execute(code="print(sum([1,2,3]))")
```

### Search
```python
# Web Search
DeepSearchTool().execute(query="python tutorial")

# RAG Search
RagSearchTool().execute(query="machine learning")
```

### HTTP/API
```python
# HTTP Request
HTTPRequestTool().execute(
    url="https://api.example.com/data",
    method="GET",
    headers={"Authorization": "Bearer token"}
)

# API Client
APIClientTool().execute(
    endpoint="https://api.example.com/users",
    method="POST",
    body={"name": "John"}
)
```

---

## 🔒 Security Layers

| Layer | Tools | Protection |
|-------|-------|-----------|
| Path Restriction | File tools | Prevents ../../ traversal |
| Code Validation | Python REPL | Blocks os.system, eval, etc |
| Timeout | Python, API | Prevents infinite loops |
| Safe Execution | All | Catches exceptions |
| Audit Log | All | Logs all operations |

---

## ⚡ Common Operations

### Read and Process File
```python
registry = ToolRegistry([FileReadTool(), PythonREPLTool()])

# Read
content = registry.execute_from_llm_response("""
{"tool": "read_file", "kwargs": {"path": "/workspace/data.txt"}}
""")

# Process
result = registry.execute_from_llm_response(f"""
{{"tool": "python_repl", "kwargs": {{"code": "print(len('{content}'))"}}}}
""")
```

### Fetch and Save Data
```python
registry = ToolRegistry([HTTPRequestTool(), FileWriteTool()])

# Fetch
data = registry.execute_from_llm_response("""
{
  "tool": "http_request",
  "kwargs": {"url": "https://api.example.com/users", "method": "GET"}
}
""")

# Save
registry.execute_from_llm_response("""
{
  "tool": "write_file",
  "kwargs": {"path": "/workspace/users.json", "content": "..."}
}
""")
```

---

## ⚠️ What's Blocked

### Code Patterns
```python
# ❌ BLOCKED
os.system()
os.popen()
subprocess.*
shutil.rmtree()
eval()
exec()
__import__()

# ✅ ALLOWED
len(), range(), sum(), max(), min()
print(), type(), str(), int()
sorted(), enumerate(), zip()
```

### File Paths
```python
# ❌ BLOCKED
/etc/passwd
/etc/shadow
../../../etc/hosts
/root/.ssh/id_rsa

# ✅ ALLOWED
/workspace/file.txt
/workspace/data/users.json
/workspace/output/result.txt
```

### URLs
```python
# ❌ BLOCKED
http://localhost:8000
http://127.0.0.1
http://192.168.1.1
http://10.0.0.1
file:///etc/passwd

# ✅ ALLOWED
https://api.example.com
https://api.github.com
https://api.openai.com
```

---

## 🔍 Debugging

### Check Available Tools
```python
registry.get_tool_names()
# ['read_file', 'write_file', 'list_dir', 'delete_file', 'create_dir',
#  'python_repl', 'search', 'rag_search', 'http_request', 'api_client']
```

### Get Tool Schema
```python
print(registry.get_tools_schema_str())
```

### Enable Logging
```python
import logging
logging.basicConfig(level=logging.INFO)
# Now all tool calls are logged
```

### Test Tool Directly
```python
tool = FileReadTool()
result = tool.execute(path="/workspace/test.txt")
if "Error" in result:
    print("Failed:", result)
```

---

## 🎯 Best Practices

✅ **DO**
- Use registry for managing multiple tools
- Enable logging for debugging
- Validate inputs before passing to tools
- Use structured JSON for LLM responses
- Test with edge cases
- Handle errors gracefully

❌ **DON'T**
- Pass untrusted code to PythonREPLTool
- Create tools outside /workspace
- Disable security decorators
- Use file:// URLs
- Ignore error messages
- Run tools without audit logging

---

## 📊 Tool Limits

| Tool | Timeout | Request | Response |
|------|---------|---------|----------|
| FileReadTool | ∞ | File size | File size |
| FileWriteTool | ∞ | 10KB | N/A |
| PythonREPLTool | 10s | Code | 1MB |
| HTTPRequestTool | 30s | 10KB | 1MB |
| APIClientTool | 30s | 10KB | 1MB |

---

## 💡 Pro Tips

1. **Chain Operations**: Use registry to chain multiple tools
2. **Error Recovery**: Always check for "Error:" in responses
3. **Logging**: Enable logging to debug tool issues
4. **Testing**: Test tools individually before using in production
5. **Performance**: Cache API responses when possible
6. **Security**: Review audit logs regularly
7. **Timeouts**: Use longer timeouts for heavy operations
8. **Validation**: Always validate external inputs

---

## 📞 Troubleshooting

### "Access denied: outside workspace"
→ Make sure path starts with `/workspace/`

### "Execution blocked: forbidden pattern"
→ Avoid: os.system, subprocess, eval, exec, __import__

### "Tool timed out"
→ Your code took too long (>10s for Python, >30s for API)

### "URL contains blocked pattern"
→ Can't access localhost, private IPs, or file:// URLs

### "Response too large"
→ Response exceeds 1MB limit (HTTPRequestTool)

### "No JSON block found"
→ LLM response must contain valid JSON with tool call

---

## 📖 Documentation

- Full docs: `core/tools/README.md`
- Security checklist: `core/tools/SECURITY_CHECKLIST.md`
- Completion summary: `TOOLS_COMPLETION_SUMMARY.md`

---

Last Updated: March 13, 2026
