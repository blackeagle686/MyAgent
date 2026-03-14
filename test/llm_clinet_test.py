from core.services import LLMClient

def test_llm_client():

    llm_client = LLMClient()

    response = llm_client.generate("What is the capital of France?")

    assert response.strip().lower() == "paris"