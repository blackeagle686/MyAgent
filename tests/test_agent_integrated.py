import logging
import sys
import os
from unittest.mock import MagicMock

# Mock heavy dependencies before they are imported by core modules
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
    "chromadb.errors",
    "sentence_transformers.SentenceTransformer"
]:
    sys.modules[module_name] = MagicMock()

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now we can safely import BrainAgent and agent_loop
from core.agent import BrainAgent
from core.agent.agent_loop import agent_loop

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_loop():
    print("Initializing Agent (Mocked)...")
    
    # Mock the LLM generate method to return a controlled sequence
    from core.services.llm_service import client
    client.generate = MagicMock()
    
    # Sequence of responses for the test
    # 1. Thinker analysis
    analysis_resp = "problem_type: file_listing\ndifficulty: easy\nneeds_tools: yes\nstrategy: use list_dir"
    # 2. Thinker decomposition
    tasks_resp = '[{"task": "List files", "priority": 5}]'
    # 3. Planner decision
    plan_resp = '{"action": "execute_tool", "tool": "list_tools", "tool_input": ".", "reasoning": "I need to see the files", "confidence": 0.9}'
    # 4. Final summary think call
    summary_resp = "FINAL_ANSWER: I have listed the files. There are several markdown and python files."
    
    client.generate.side_effect = [analysis_resp, tasks_resp, plan_resp, summary_resp, "Past experience summary"]

    # Mock act to return dummy observation
    agent = BrainAgent(sys_prompt="You are a helpful assistant.")
    agent.act = MagicMock(return_value="file1.py, file2.md")
    
    user_prompt = "Hello! Can you list the files?"
    
    print(f"Running agent loop with prompt: '{user_prompt}'")
    try:
        final_answer = agent_loop(agent, user_prompt, max_steps=2)
        print("\n" + "="*50)
        print("FINAL ANSWER:")
        print(final_answer)
        print("="*50)
        
        # Verify calls
        assert agent.act.called, "agent.act should have been called"
        print("Test passed: Flow executed correctly with mocks.")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_loop()

