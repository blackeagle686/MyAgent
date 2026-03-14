import logging

# Configure logging to see the output
logging.basicConfig(level=logging.INFO, format='%(message)s')

from core.agent.agent_build import BrainAgent
from core.agent.agent_loop import agent_loop

print("\n--- Initializing BrainAgent ---")
try:
    agent = BrainAgent(sys_prompt="You are a helpful AI designed to solve problems step by step.")
    
    # Let's see if the tools and memory initialized correctly
    print("Tools registered:")
    for tool_name in agent.tools:
        print(f" - {tool_name.name}: {tool_name.description}")
        
    print("\n--- Running Agent Loop ---")
    user_prompt = "What is 2 + 2? Show me a python script that prints it."
    
    # Note: We won't actually hit the LLM API effectively unless keys are valid and working,
    # but we will see if parsing and structure hold up or if missing imports crash it.
    final_answer = agent_loop(agent, user_prompt, max_steps=2)
    
    print("\n--- Final Output ---")
    print(final_answer)
    
except Exception as e:
    import traceback
    traceback.print_exc()
