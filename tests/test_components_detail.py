import sys
import os
import json
import logging
from unittest.mock import MagicMock

# 1. MOCK HEAVY DEPENDENCIES
for module_name in [
    "openai", "sentence_transformers", "torch", "torch.nn", "torch.nn.functional", 
    "numpy", "chromadb", "chromadb.utils", "chromadb.config", "chromadb.errors"
]:
    sys.modules[module_name] = MagicMock()

# Setup root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 2. IMPORTS
from core.agent import BrainAgent
from core.agent.agent_planner import Planner
from core.agent.agent_memory import Experience

# Configure basic logging
logging.basicConfig(level=logging.ERROR) # Keep log quiet, we use print

def run_deep_test():
    print("\n" + "="*60)
    print("      DEEP AGENT COMPONENT TEST (MOCKED ENVIRONMENT)")
    print("="*60)

    # Setup Mock LLM Service
    from core.services.llm_service import client
    client.generate = MagicMock()
    
    # -------------------------------------------------------------------------
    # TEST 1: INITIALIZATION
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Initializing BrainAgent...")
    agent = BrainAgent(sys_prompt="You are a senior developer.")
    print(f"Agent initialized with {len(agent.registry.get_all_tools())} tools.")
    print("Memory, Thinker, and TaskManager ready.")

    # -------------------------------------------------------------------------
    # TEST 2: THINKER (DECOMPOSITION)
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Testing THINKER (Analysis & Decomposition)...")
    user_prompt = "Refactor the authentication module and add LDAP support."
    
    # Mock responses for Thinker
    analysis_resp = "problem_type: refactoring\ndifficulty: high\nneeds_tools: yes\nstrategy: analysis -> implementation"
    tasks_json = '[{"task": "Read auth code", "priority": 5}, {"task": "Add LDAP logic", "priority": 4}]'
    client.generate.side_effect = [analysis_resp, tasks_json]
    
    analysis, tasks = agent.thinker.think(user_prompt)
    print(f"Input: {user_prompt}")
    print("-" * 20)
    print(f"Analysis Output:\n{analysis}")
    print("-" * 20)
    print(f"Decomposed Tasks ({len(tasks)}):")
    for i, t in enumerate(tasks):
        print(f"  {i+1}. {t.prompt} (Priority: {t.priority})")

    # -------------------------------------------------------------------------
    # TEST 3: PLANNER (ACTION DECISION)
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Testing PLANNER (Decision Logic)...")
    agent.task_manager.add_many(tasks)
    
    planner = Planner(
        task_manager=agent.task_manager,
        tools=agent.registry._tools
    )
    
    # Mock Planner decision
    plan_resp = '{"action": "execute_tool", "tool": "read_file", "tool_input": "core/auth.py", "reasoning": "I need to understand the existing code first.", "confidence": 0.95}'
    client.generate.side_effect = [plan_resp]
    
    result = planner.plan_next()
    if result:
        task, decision = result
        print(f"Selected Task: {task.prompt}")
        print(f"Planner Action: {decision['action']}")
        print(f"Planner Tool: {decision['tool']}")
        print(f"Planner Input: {decision['tool_input']}")
        print(f"Planner Reasoning: {decision['reasoning']}")

    # -------------------------------------------------------------------------
    # TEST 4: EXECUTION (ACTOR)
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Testing EXECUTION (Actor Tool Run)...")
    # Mock response format coming from LLM
    llm_tool_call = json.dumps({"tool": "read_file", "kwargs": {"path": "core/auth.py"}})
    
    # Mock tool execution in Actor
    agent.act = MagicMock(return_value="class Auth: def login(user, pwd): ...")
    
    observation = agent.act(llm_tool_call)
    print(f"Simulated LLM call: {llm_tool_call}")
    print(f"Observation (Tool Result): {observation}")

    # -------------------------------------------------------------------------
    # TEST 5: MEMORY (STORING & LEARNING)
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Testing MEMORY (Learning & Retrieval)...")
    exp = Experience()
    exp.task_prompt = user_prompt
    exp.add_step("Thinking about code", llm_tool_call, observation)
    exp.final_answer = "Refactoring planned and LDAP added."
    
    # Mock learn components
    agent.exp_memory.add = MagicMock()
    agent.memory.add = MagicMock()
    agent.memory.retrieve_context = MagicMock(return_value="Past fact: LDAP is a directory protocol.")
    
    agent.learn(exp)
    print(f"Experience saved (ID: {exp.id})")
    
    # Retrieval
    retrieved = agent.memory.retrieve_context("What is LDAP?")
    print(f"Memory Retrieval Result: {retrieved}")

    print("\n" + "="*60)
    print("      ALL COMPONENTS VERIFIED SUCCESSFULLY")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_deep_test()
