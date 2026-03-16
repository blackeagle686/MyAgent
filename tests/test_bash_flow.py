import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from core.agent.agent_build import BrainAgent
from core.agent.agent_loop import agent_loop

def test_bash_flow():
    agent = BrainAgent(sys_prompt="You are a helpful assistant. TEST MODE.")
    
    # Prompt requiring bash execution
    prompt = (
        "1. Write a bash script named 'list_test.sh' that lists all files in the 'gui/' directory "
        "and searches for the word 'MODERN' inside 'styles.py'. "
        "2. Execute the created script using the bash_execute tool and show me the output."
    )
    
    print(f"Testing with prompt: {prompt}")
    result = agent_loop(agent, prompt, max_steps=5)
    print(f"Final Result: {result}")
    
    # Cleanup
    if os.path.exists("list_test.sh"):
        os.remove("list_test.sh")

if __name__ == "__main__":
    test_bash_flow()
