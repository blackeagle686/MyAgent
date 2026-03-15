import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from core.services.llm_service import client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_summary():
    with open("ARCHITECTURE.md", "r") as f:
        content = f.read()
    
    print(f"Content length: {len(content)} characters")
    
    try:
        print("Sending request...")
        response = client.generate(
            user_prompt=f"Summarize this:\n\n{content}",
            sys_prompt="Summarize the key architectural components."
        )
        print("Response received:")
        print(response)
    except Exception as e:
        print(f"Caught exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_summary()
