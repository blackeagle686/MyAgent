import logging
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies before they are imported by core modules
# Using simple MagicMocks to avoid recursion issues
for module_name in [
    "openai", 
    "sentence_transformers", 
    "torch", 
    "torch.nn", 
    "torch.nn.functional", 
    "numpy",
    "chromadb",
    "chromadb.utils",
    "chromadb.config",
    "chromadb.errors"
]:
    sys.modules[module_name] = MagicMock()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from core.agent.agent_build import BrainAgent
from core.agent.agent_loop import agent_loop

print("\n--- Initializing BrainAgent (Mocked) ---")
try:
    # Set up mock responses for LLM
    from core.services.llm_service import client
    client.generate = MagicMock()
    
    # Side effects to cover all think/plan/summary calls
    client.generate.side_effect = [
        "problem_type: calculus\ndifficulty: easy\nneeds_tools: yes\nstrategy: code", # Thinker analysis
        '[{"task": "calculate 2+2", "priority": 5}]', # Thinker decompose
        '{"action": "execute_tool", "tool": "python_repl", "tool_input": "print(2+2)", "reasoning": "Simple math", "confidence": 1.0}', # Planner
        "FINAL_ANSWER: 2 + 2 is 4.", # Summary call
        "Experience Summary" # Learn call
    ]

    agent = BrainAgent(sys_prompt="You are a helpful AI.")
    
    # Mock act to return dummy observation
    agent.act = MagicMock(return_value="4")
    
    print("Tools registered:")
    for tool in agent.registry.get_all_tools():
        print(f" - {tool.name}: {tool.description}")
        
    print("\n--- Running Agent Loop ---")
    user_prompt = "What is 2 + 2?"
    
    final_answer = agent_loop(agent, user_prompt, max_steps=5)
    
    print("\n" + "="*50)
    print("FINAL ANSWER:")
    print(final_answer)
    print("="*50)
    print("\nTest passed: Integrated loop completed successfully.")
    
except Exception as e:
    import traceback
    traceback.print_exc()
