"""
AgentActor Examples and Tests
==============================
Demonstrates the AgentActor usage and capabilities.
"""

import json
from core.agent.agent_actor import AgentActor, ToolCall
from core.tools import (
    ToolRegistry,
    FileReadTool,
    FileWriteTool,
    ListDirTool,
    PythonREPLTool,
)


# =============================================================================
# Example 1: Basic Tool Execution
# =============================================================================

def example_basic_execution():
    """Simple tool execution through the actor."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Tool Execution")
    print("="*70)
    
    # Setup
    registry = ToolRegistry([FileReadTool()])
    actor = AgentActor(registry)
    
    # LLM generates response with tool call
    llm_response = """
    I'll read the file to see what's inside.
    
    ```json
    {"tool": "read_file", "kwargs": {"path": "/workspace/test.txt"}}
    ```
    """
    
    # Actor executes the tool
    observation = actor.act(llm_response)
    print(f"\nLLM Response:\n{llm_response}")
    print(f"\nObservation:\n{observation}")
    print(f"\nExecution Stats: {actor.get_execution_stats()}")


# =============================================================================
# Example 2: Error Handling - Tool Not Found
# =============================================================================

def example_tool_not_found():
    """Handling when tool doesn't exist."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Tool Not Found Error")
    print("="*70)
    
    registry = ToolRegistry([FileReadTool()])
    actor = AgentActor(registry)
    
    llm_response = """
    Let me search the web for this information.
    
    ```json
    {"tool": "web_search", "kwargs": {"query": "machine learning"}}
    ```
    """
    
    observation = actor.act(llm_response)
    print(f"\nLLM Response:\n{llm_response}")
    print(f"\nObservation (Error):\n{observation}")
    print(f"\nAvailable Tools: {actor.registry.get_tool_names()}")


# =============================================================================
# Example 3: Error Handling - Invalid JSON
# =============================================================================

def example_invalid_json():
    """Handling malformed JSON."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Invalid JSON")
    print("="*70)
    
    registry = ToolRegistry([FileReadTool()])
    actor = AgentActor(registry)
    
    llm_response = """
    Let me read the file.
    
    ```json
    {"tool": "read_file", "kwargs": {"path": "/file.txt" INVALID}
    ```
    """
    
    observation = actor.act(llm_response)
    print(f"\nLLM Response:\n{llm_response}")
    print(f"\nObservation (Error):\n{observation}")


# =============================================================================
# Example 4: Multiple Tools in Registry
# =============================================================================

def example_multiple_tools():
    """Actor with multiple tools available."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Multiple Tools")
    print("="*70)
    
    registry = ToolRegistry([
        FileReadTool(),
        FileWriteTool(),
        ListDirTool(),
        PythonREPLTool(),
    ])
    
    actor = AgentActor(registry)
    
    print(f"\nAvailable Tools: {actor.registry.get_tool_names()}")
    
    # Tool 1: List directory
    print("\n--- Tool 1: List Directory ---")
    response1 = '{"tool": "list_dir", "kwargs": {"path": "/workspace"}}'
    obs1 = actor.act(response1)
    print(f"Observation: {obs1[:100]}...")
    
    # Tool 2: Python execution
    print("\n--- Tool 2: Python REPL ---")
    response2 = '{"tool": "python_repl", "kwargs": {"code": "print(sum([1,2,3]))"}}'
    obs2 = actor.act(response2)
    print(f"Observation: {obs2}")
    
    # Stats
    print(f"\n--- Execution Stats ---")
    stats = actor.get_execution_stats()
    print(f"Total Executions: {stats['total_executions']}")
    for i, execution in enumerate(stats['history'], 1):
        print(f"{i}. {execution['tool']}: {str(execution['result'])[:50]}...")


# =============================================================================
# Example 5: Parsing Strategies
# =============================================================================

def example_parsing_strategies():
    """Different JSON extraction strategies."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Parsing Strategies")
    print("="*70)
    
    registry = ToolRegistry([FileReadTool()])
    actor = AgentActor(registry)
    
    # Strategy 1: Markdown code block
    print("\n--- Strategy 1: Markdown Code Block ---")
    response1 = """
    I need to read this file:
    
    ```json
    {"tool": "read_file", "kwargs": {"path": "/workspace/data.txt"}}
    ```
    
    Let me process the contents.
    """
    debug1 = actor.debug_parse(response1)
    print(f"Parsed: {debug1['parsed']}")
    print(f"Tool: {debug1['tool_call']['name']}")
    
    # Strategy 2: Plain JSON
    print("\n--- Strategy 2: Plain JSON ---")
    response2 = """
    Reading file...
    {"tool": "read_file", "kwargs": {"path": "/workspace/config.txt"}}
    Done!
    """
    debug2 = actor.debug_parse(response2)
    print(f"Parsed: {debug2['parsed']}")
    print(f"Tool: {debug2['tool_call']['name']}")
    
    # Strategy 3: No JSON
    print("\n--- Strategy 3: No JSON ---")
    response3 = "I need to read a file but forgot to provide the JSON."
    debug3 = actor.debug_parse(response3)
    print(f"Parsed: {debug3['parsed']}")


# =============================================================================
# Example 6: Execution History
# =============================================================================

def example_execution_history():
    """Tracking execution history."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Execution History")
    print("="*70)
    
    registry = ToolRegistry([PythonREPLTool()])
    actor = AgentActor(registry)
    
    # Execute multiple operations
    operations = [
        '{"tool": "python_repl", "kwargs": {"code": "x = 5"}}',
        '{"tool": "python_repl", "kwargs": {"code": "print(x * 2)"}}',
        '{"tool": "python_repl", "kwargs": {"code": "print(sum(range(1, 11)))"}}',
    ]
    
    for i, op in enumerate(operations, 1):
        result = actor.act(op)
        print(f"\nOperation {i}:")
        print(f"  Response: {op}")
        print(f"  Result: {result}")
    
    # Show history
    print(f"\n--- Full History ---")
    stats = actor.get_execution_stats()
    print(f"Total Executions: {stats['total_executions']}")
    
    for i, execution in enumerate(stats['history'], 1):
        print(f"\n{i}. Tool: {execution['tool']}")
        print(f"   Args: {execution['args']}")
        print(f"   Time: {execution['timestamp']:.4f}s")
        print(f"   Result: {execution['result'][:60]}...")


# =============================================================================
# Example 7: Debug Parsing
# =============================================================================

def example_debug_parsing():
    """Using debug_parse to troubleshoot."""
    print("\n" + "="*70)
    print("EXAMPLE 7: Debug Parsing")
    print("="*70)
    
    registry = ToolRegistry([
        FileReadTool(),
        FileWriteTool(),
        ListDirTool(),
    ])
    
    actor = AgentActor(registry)
    
    # Problematic response
    response = """
    Let me work on this task:
    
    ```json
    {"tool": "unknown_tool", "kwargs": {"path": "/file.txt"}}
    ```
    """
    
    debug_info = actor.debug_parse(response)
    
    print(f"\nDebug Information:")
    print(f"  Parsed Successfully: {debug_info['parsed']}")
    print(f"  Tool Name: {debug_info['tool_call']['name']}")
    print(f"  Tool Exists: {debug_info['tool_call']['name'] in debug_info['available_tools']}")
    print(f"  Available Tools: {', '.join(debug_info['available_tools'])}")
    print(f"  Response Preview: {debug_info['raw_response_preview']}")


# =============================================================================
# Example 8: Complex JSON Arguments
# =============================================================================

def example_complex_arguments():
    """Tool calls with complex arguments."""
    print("\n" + "="*70)
    print("EXAMPLE 8: Complex Arguments")
    print("="*70)
    
    registry = ToolRegistry([PythonREPLTool()])
    actor = AgentActor(registry)
    
    # Complex code with multiline and special characters
    response = """
    Let me execute a complex calculation:
    
    ```json
    {
        "tool": "python_repl",
        "kwargs": {
            "code": "result = sum([i**2 for i in range(1, 11)])\\nprint(f'Sum of squares 1-10: {result}')"
        }
    }
    ```
    """
    
    observation = actor.act(response)
    print(f"\nResponse:\n{response}")
    print(f"\nObservation:\n{observation}")


# =============================================================================
# Main: Run All Examples
# =============================================================================

def main():
    """Run all examples."""
    print("\n" + "#"*70)
    print("# AgentActor Examples & Demonstrations")
    print("#"*70)
    
    try:
        example_basic_execution()
    except Exception as e:
        print(f"Example 1 Error: {e}")
    
    try:
        example_tool_not_found()
    except Exception as e:
        print(f"Example 2 Error: {e}")
    
    try:
        example_invalid_json()
    except Exception as e:
        print(f"Example 3 Error: {e}")
    
    try:
        example_multiple_tools()
    except Exception as e:
        print(f"Example 4 Error: {e}")
    
    try:
        example_parsing_strategies()
    except Exception as e:
        print(f"Example 5 Error: {e}")
    
    try:
        example_execution_history()
    except Exception as e:
        print(f"Example 6 Error: {e}")
    
    try:
        example_debug_parsing()
    except Exception as e:
        print(f"Example 7 Error: {e}")
    
    try:
        example_complex_arguments()
    except Exception as e:
        print(f"Example 8 Error: {e}")
    
    print("\n" + "#"*70)
    print("# All Examples Completed")
    print("#"*70 + "\n")


if __name__ == "__main__":
    main()
