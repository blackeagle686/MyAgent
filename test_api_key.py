import requests
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from config import Config

def test_key():
    print(f"Testing key: {Config.api_key[:10]}...")
    headers = {
        "Authorization": f"Bearer {Config.api_key}",
        "Content-Type": "application/json"
    }
    
    # Test completion
    data = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [{"role": "user", "content": "Say hello"}]
    }
    
    print("Testing completion...")
    resp = requests.post(
        f"{Config.base_url}/chat/completions",
        headers=headers,
        data=json.dumps(data)
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")

    # Test embedding
    embed_data = {
        "model": Config.embedding_model,
        "input": "test"
    }
    print("\nTesting embedding...")
    resp_embed = requests.post(
        f"{Config.base_url}/embeddings",
        headers=headers,
        data=json.dumps(embed_data)
    )
    print(f"Status: {resp_embed.status_code}")
    print(f"Response: {resp_embed.text}")

if __name__ == "__main__":
    test_key()
