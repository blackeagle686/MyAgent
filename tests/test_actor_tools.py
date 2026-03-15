import sys
import os
import json
from unittest.mock import MagicMock

# 1. MOCK HEAVY DEPENDENCIES
for module_name in [
    "openai", "sentence_transformers", "torch", "torch.nn", "torch.nn.functional", 
    "numpy", "chromadb", "chromadb.utils", "chromadb.config", "chromadb.errors"
]:
    sys.modules[module_name] = MagicMock()

# Setup root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.agent.agent_actor import AgentActor
from core.tools.registry import ToolRegistry
from core.tools.file_system import ListDirTool
from core.tools.python_repl import PythonREPLTool

def run_actor_tools_test():
    print("\n" + "="*60)
    print("      ACTOR AND TOOLS VERIFICATION TEST")
    print("="*60)

    # -------------------------------------------------------------------------
    # SETUP
    # -------------------------------------------------------------------------
    # Register some tools to test with
    tools = [ListDirTool(), PythonREPLTool()]
    registry = ToolRegistry(tools=tools)
    actor = AgentActor(registry=registry)
    
    # -------------------------------------------------------------------------
    # TEST 1: PARSING DIFFERENT FORMATS
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Parsing LLM Responsess...")
    
    # Format A: Markdown Code Block
    resp_a = "I will list the files.\n```json\n{\"tool\": \"list_dir\", \"kwargs\": {\"path\": \".\"}}\n```"
    # Format B: Raw JSON
    resp_b = "{\"tool\": \"python_repl\", \"kwargs\": {\"code\": \"print(1+1)\"}}"
    # Format C: Text with JSON inside
    resp_c = "Let's try this: {\"tool\": \"list_dir\", \"kwargs\": {\"path\": \"/tmp\"}} and see."

    for i, resp in enumerate([resp_a, resp_b, resp_c]):
        print(f"  Attempting to parse response format {chr(65+i)}...")
        # Use the internal _parse_tool_call to verify parsing
        tool_call = actor._parse_tool_call(resp)
        if tool_call:
            print(f"  Successfully parsed: {tool_call.tool_name} with {len(tool_call.kwargs)} args")
        else:
            print(f"  Failed to parse from: {resp[:30]}...")

    # -------------------------------------------------------------------------
    # TEST 2: TOOL EXECUTION VIA ACTOR
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Executing Tools via Actor...")
    
    # Mock the actual tool execution to avoid side effects on the system during test
    for tool in tools:
        if isinstance(tool, ListDirTool):
            tool.execute = MagicMock(return_value="file_a.txt, file_b.py")
        if isinstance(tool, PythonREPLTool):
            tool.execute = MagicMock(return_value="2\n")

    # Run ListDir
    obs_a = actor.act(resp_a)
    print(f"  Action A (ListDir) Observation: {obs_a}")
    
    # Run PythonREPL
    obs_b = actor.act(resp_b)
    print(f"  Action B (PythonREPL) Observation: {obs_b}")

    # -------------------------------------------------------------------------
    # TEST 3: UNKNOWN TOOL HANDLING
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Unknown Tool Handling...")
    resp_unknown = "```json\n{\"tool\": \"missing_tool\", \"kwargs\": {}}\n```"
    obs_unknown = actor.act(resp_unknown)
    print(f"  Unknown Tool Result: {obs_unknown}")

    print("\n" + "="*60)
    print("      ACTOR AND TOOLS TEST COMPLETED")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_actor_tools_test()
