# AgentActor - Visual Architecture Guide

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     ReAct Agent Loop                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Step 1: THINK                                                   │
│  ┌────────────────────────────────────────────────────────┐      │
│  │ Agent generates reasoning + tool call decision         │      │
│  │ Using: LLM, Memory, Task Manager                       │      │
│  └────────────────────────────────────────────────────────┘      │
│                            ↓                                     │
│                                                                   │
│  Step 2: ACT (AgentActor)                                       │
│  ┌────────────────────────────────────────────────────────┐      │
│  │ 1. Parse JSON tool call from LLM response              │      │
│  │ 2. Validate tool existence & arguments                 │      │
│  │ 3. Execute tool via registry                           │      │
│  │ 4. Return observation                                  │      │
│  └────────────────────────────────────────────────────────┘      │
│                            ↓                                     │
│                                                                   │
│  Step 3: OBSERVE                                                 │
│  ┌────────────────────────────────────────────────────────┐      │
│  │ Tool result becomes part of agent context              │      │
│  │ Continue reasoning or return FINAL_ANSWER              │      │
│  └────────────────────────────────────────────────────────┘      │
│                                                                   │
│  Loop continues until: FINAL_ANSWER or max_steps reached        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## AgentActor Internal Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                    act(llm_response: str)                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  START                                                                │
│    ↓                                                                  │
│  ┌─────────────────────────────────────┐                             │
│  │ PHASE 1: PARSE                      │                             │
│  │                                     │                             │
│  │ Input: Raw LLM response text        │                             │
│  │ Output: ToolCall object or None     │                             │
│  │                                     │                             │
│  │ Strategy 1:                         │                             │
│  │   ```json {...} ``` ─→ Extract      │                             │
│  │                                     │                             │
│  │ Strategy 2:                         │                             │
│  │   {...} ─→ Extract                  │                             │
│  │                                     │                             │
│  │ Result: ToolCall(name, kwargs, raw) │                             │
│  └─────────────────────────────────────┘                             │
│    ↓                                                                  │
│    NO                       YES                                       │
│    ├─→ Return "[ERROR]"   ──┤                                        │
│    │   No tool call found     │                                      │
│    │                          ↓                                      │
│    │   ┌──────────────────────────────────────┐                      │
│    │   │ PHASE 2: VALIDATE                    │                      │
│    │   │                                      │                      │
│    │   │ Check 1: Tool name valid?            │                      │
│    │   │   ✓ Non-empty string                 │                      │
│    │   │                                      │                      │
│    │   │ Check 2: Tool exists in registry?    │                      │
│    │   │   ✓ registry.get_tool(name)          │                      │
│    │   │                                      │                      │
│    │   │ Check 3: Kwargs is dict?             │                      │
│    │   │   ✓ isinstance(kwargs, dict)         │                      │
│    │   │                                      │                      │
│    │   │ Check 4: Size reasonable?            │                      │
│    │   │   ✓ json.dumps(kwargs) < 100KB       │                      │
│    │   │                                      │                      │
│    │   └──────────────────────────────────────┘                      │
│    │    ↓                                                             │
│    │    INVALID         VALID                                         │
│    │    ├─→ Return  ────┤                                            │
│    │    │   "[ERROR]"   │                                            │
│    │    │   (specific    │                                            │
│    │    │    reason)     ↓                                            │
│    │    │   ┌────────────────────────────────────────┐               │
│    │    │   │ PHASE 3: EXECUTE                       │               │
│    │    │   │                                        │               │
│    │    │   │ 1. Get tool from registry              │               │
│    │    │   │ 2. Call tool.execute(**kwargs)         │               │
│    │    │   │ 3. Convert result to string            │               │
│    │    │   │ 4. Record in execution history         │               │
│    │    │   │                                        │               │
│    │    │   │ result = tool.execute(...)             │               │
│    │    │   │ observation = str(result)              │               │
│    │    │   │                                        │               │
│    │    │   └────────────────────────────────────────┘               │
│    │    │    ↓                                                        │
│    │    │    SUCCESS          EXCEPTION                              │
│    │    │    ├─→ Return       ─→ Catch & Log                         │
│    │    │    │   observation      Return "[ERROR]..."               │
│    │    │    │                                                        │
│    │    │    ↓                                                        │
│    │    │  RETURN OBSERVATION                                        │
│    │    │  To agent loop                                             │
│    │    │                                                            │
│    ↓                                                                  │
│  END                                                                  │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Class Structure

```
┌────────────────────────────────────────────────────────────────┐
│                      AgentActor                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ATTRIBUTES                                                    │
│  ├─ registry: ToolRegistry        # Tools to execute            │
│  ├─ _execution_count: int         # Number of executions        │
│  └─ _execution_history: list      # Execution log               │
│                                                                 │
│  PUBLIC METHODS                                                │
│  ├─ act(llm_response) → str                                    │
│  │   └─ Parse, validate, execute tool                         │
│  │                                                             │
│  ├─ get_execution_stats() → Dict                              │
│  │   └─ Return execution history                              │
│  │                                                             │
│  ├─ reset_history() → None                                    │
│  │   └─ Clear execution log                                   │
│  │                                                             │
│  └─ debug_parse(response) → Dict                              │
│      └─ Debug parsing information                             │
│                                                                 │
│  PRIVATE METHODS (Parsing)                                    │
│  ├─ _parse_tool_call(response) → ToolCall?                    │
│  │   ├─ _extract_markdown_json()                              │
│  │   └─ _extract_plain_json()                                 │
│  │                                                             │
│  PRIVATE METHODS (Validation)                                 │
│  ├─ _validate_tool_call(tool_call) → (bool, str)              │
│  │                                                             │
│  PRIVATE METHODS (Execution)                                  │
│  ├─ _execute_tool(tool_call) → str                            │
│  │                                                             │
│  PRIVATE METHODS (Formatting)                                 │
│  ├─ _format_error(msg) → str                                  │
│  └─ _format_result(result, tool_name) → str                   │
│                                                                 │
└────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐
│         ToolCall (Dataclass)         │
├─────────────────────────────────────┤
│ tool_name: str                       │
│ kwargs: Dict[str, Any]               │
│ raw_text: str                        │
└─────────────────────────────────────┘

┌──────────────────────────────────────┐
│       ActorResult (Dataclass)        │
├──────────────────────────────────────┤
│ success: bool                         │
│ observation: str                      │
│ tool_name: Optional[str]             │
│ error: Optional[str]                 │
│ execution_time: float                │
└──────────────────────────────────────┘
```

## Integration Points

```
┌──────────────────────────────────────────────────────────┐
│                  BrainAgent                              │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  think(prompt) → str                                     │
│    └─ Uses: LLM, Memory, TaskManager                    │
│       Output: Reasoning + tool call JSON                │
│              (JSON: {"tool": "...", "kwargs": {...}})   │
│                                                           │
│  act(llm_response) → str                                │
│    └─ Uses: AgentActor.act()                            │
│       Input: LLM response with JSON                     │
│       Output: Tool result (observation)                 │
│                    ↓                                    │
│  ┌─────────────────────────────────────┐                │
│  │      AgentActor ← Interface         │                │
│  ├─────────────────────────────────────┤                │
│  │ • Parse JSON                        │                │
│  │ • Validate arguments                │                │
│  │ • Execute via ToolRegistry          │                │
│  │ • Return observation                │                │
│  └─────────────────────────────────────┘                │
│                    ↓                                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │         ToolRegistry                             │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ • Stores tool instances                          │   │
│  │ • Validates tool calls                           │   │
│  │ • Executes tools                                 │   │
│  │ • Returns results                                │   │
│  └──────────────────────────────────────────────────┘   │
│                    ↓                                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │      Individual Tools                            │   │
│  ├──────────────────────────────────────────────────┤   │
│  │ • FileReadTool                                   │   │
│  │ • FileWriteTool                                  │   │
│  │ • PythonREPLTool                                 │   │
│  │ • HTTPRequestTool                                │   │
│  │ • ... (custom tools)                             │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
│  learn(experience) → None                               │
│    └─ Uses: MemoryStore, ExperienceMemory              │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## Data Flow in ReAct Loop

```
ITERATION 1
──────────

  USER PROMPT
  "Analyze the data in /workspace/data.csv"
        │
        ↓
  ┌──────────────────────────────────────┐
  │ agent.think(prompt)                  │
  │ LLM generates thought + action       │
  └──────────────────────────────────────┘
        │
        ↓
  LLM OUTPUT:
  "I'll read the file first to understand its structure.
   
   ```json
   {"tool": "read_file", "kwargs": {"path": "/workspace/data.csv"}}
   ```"
        │
        ↓
  ┌──────────────────────────────────────┐
  │ agent.act(llm_response)              │
  │   → actor.act(response)              │
  └──────────────────────────────────────┘
        │
        ├─ Parse: Extract JSON
        ├─ Validate: Tool exists, args valid
        ├─ Execute: FileReadTool.execute()
        └─ Return: File contents
        │
        ↓
  OBSERVATION:
  "File content of /workspace/data.csv:
   id,name,value
   1,apple,100
   2,banana,200
   ..."
        │
        ↓
  ┌──────────────────────────────────────┐
  │ Update trajectory                    │
  │ Continue loop                        │
  └──────────────────────────────────────┘


ITERATION 2
──────────

  USER PROMPT + TRAJECTORY + OBSERVATION
        │
        ↓
  ┌──────────────────────────────────────┐
  │ agent.think(prompt, trajectory)      │
  │ LLM generates next action            │
  └──────────────────────────────────────┘
        │
        ↓
  LLM OUTPUT:
  "Now I'll analyze the data with Python.
   
   ```json
   {
     "tool": "python_repl",
     "kwargs": {
       "code": "import pandas as pd\\ndf = pd.read_csv('/workspace/data.csv')\\nprint(df.describe())"
     }
   }
   ```"
        │
        ↓
  ┌──────────────────────────────────────┐
  │ agent.act(llm_response)              │
  │   → actor.act(response)              │
  └──────────────────────────────────────┘
        │
        ├─ Parse: Extract JSON with multiline code
        ├─ Validate: Tool exists, code valid
        ├─ Execute: PythonREPLTool.execute()
        └─ Return: Analysis output
        │
        ↓
  OBSERVATION:
  "       id        name      value
   count   2.0      2.000    2.00000
   mean    1.5   [avg]      150.00000
   ..."
        │
        ↓
  Continue until FINAL_ANSWER

FINAL OUTPUT
──────────

  FINAL_ANSWER: "The dataset has 2 rows. Column values average to 150."
```

## Error Handling Decision Tree

```
Agent calls act(llm_response)
    │
    ├─ No JSON found?
    │  └─ Return: "[ERROR] No tool call found..."
    │
    ├─ JSON parse error?
    │  └─ Return: "[ERROR] JSON parse error..."
    │
    ├─ Tool name missing?
    │  └─ Return: "[ERROR] No 'tool' key found..."
    │
    ├─ Tool not registered?
    │  └─ Return: "[ERROR] Tool 'X' not found. Available: [...]"
    │
    ├─ Kwargs not dict?
    │  └─ Return: "[ERROR] Tool kwargs must be dict"
    │
    ├─ Kwargs too large?
    │  └─ Return: "[ERROR] Arguments too large (max 100KB)"
    │
    ├─ Tool raises exception?
    │  ├─ Catch exception
    │  ├─ Log error
    │  └─ Return: "[ERROR] Error executing tool: ..."
    │
    └─ Success!
       └─ Return: "[tool_result]" (observation)
```

## Execution History Structure

```
execution_history = [
    {
        "tool": "read_file",
        "args": {"path": "/workspace/file.txt"},
        "result": "File content...",
        "timestamp": 0.234  # seconds
    },
    {
        "tool": "python_repl",
        "args": {"code": "x = 5\nprint(x)"},
        "result": "5",
        "timestamp": 0.567
    },
    ...
]
```

## Logging Levels

```
DEBUG   - Detailed parsing info, argument values
INFO    - Tool execution start/completion, timing
WARNING - Tools already registered, unusual patterns
ERROR   - Parse failures, validation failures, exceptions
```

Example log output:

```
INFO:agent_actor:Parsed tool call: read_file with args {'path': '/file.txt'}
INFO:agent_actor:Executing tool: read_file
DEBUG:agent_actor:Arguments: {'path': '/file.txt'}
DEBUG:agent_actor:Tool result: File content of /workspace/file...
INFO:agent_actor:Tool execution completed in 0.23s: read_file
```

---

**Visual Architecture Complete** ✅
