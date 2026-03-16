#!/usr/bin/env python3
import argparse
import sys
import logging
import os
from unittest.mock import MagicMock

def setup_mocks():
    """Mocks heavy dependencies to allow running without full environment setup."""
    print("⚠️  Warning: Running in MOCK mode. Heavy dependencies will be mocked.")
    for module_name in [
        "openai", "sentence_transformers", "torch", "torch.nn", "torch.nn.functional", 
        "numpy", "chromadb", "chromadb.utils", "chromadb.config", "chromadb.errors"
    ]:
        if module_name not in sys.modules:
            sys.modules[module_name] = MagicMock()


import os

def print_banner():

    os.system(r'''
(
echo ""
echo "           ,~."
echo "          (o o)"
echo "     ----(  V  )----"
echo "           U U"
echo ""
echo "        >>> MyAgent <<<"
echo ""
) | lolcat -a -d 3
''')

    os.system('toilet -f mono12 -F metal "MY AGENT" | lolcat -a')

    print()


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Run the BrainAgent Loop")
    parser.add_argument("prompt", type=str, help="The user prompt to send to the agent")
    parser.add_argument("--mock", action="store_true", help="Run with mocked dependencies (no API keys required)")
    parser.add_argument("--steps", type=int, default=10, help="Maximum number of steps in the agent loop")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()

    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')

    if args.mock:
        setup_mocks()
        # setup mock side effects for the LLM if mocking
        # This is just a basic example for mock mode
        from core.services.llm_service import client
        client.generate = MagicMock()
        client.generate.side_effect = [
            "problem_type: general\ndifficulty: easy\nneeds_tools: no\nstrategy: direct_answer", # Thinker analysis
            "[]", # Thinker tasks
            "FINAL_ANSWER: Hello! I am running in mock mode. You asked: " + args.prompt, # Planner/Summary
            "Mock memory summary" # Learning
        ]

    # Import agent components
    try:
        from core.agent import BrainAgent
        from core.agent.agent_loop import agent_loop
    except ImportError as e:
        print(f"❌ Error: Could not import agent components. Ensure you are in the project root. {e}")
        sys.exit(1)

    print(f"\n🚀 Initializing BrainAgent...")
    agent = BrainAgent(sys_prompt="You are a helpful and intelligent AI assistant.")
    
    print(f"🤖 Agent is thinking about: '{args.prompt}'")
    print("-" * 40)
    
    try:
        final_answer = agent_loop(agent, args.prompt, max_steps=args.steps)
        print("\n" + "="*60)
        print("✅ FINAL ANSWER:")
        print(final_answer)
        print("="*60 + "\n")
    except Exception as e:
        print(f"❌ Error during agent execution: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
