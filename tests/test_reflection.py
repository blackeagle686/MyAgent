import pytest
from unittest.mock import MagicMock
from core.agent.agent_memory import Experience, TrajectoryStep
from core.agent.agent_reflection import Reflector

def test_reflection_logic():
    # 1. Setup a mock experience with a "failure"
    exp = Experience()
    exp.task_prompt = "Read the contents of 'secret.txt'"
    exp.add_step(
        thought="I will try to read secret.txt",
        tool_call='{"tool": "read_file", "kwargs": {"path": "secret.txt"}}',
        observation="Error: File not found"
    )
    exp.add_step(
        thought="Maybe I should try again?",
        tool_call='{"tool": "read_file", "kwargs": {"path": "secret.txt"}}',
        observation="Error: File not found"
    )
    exp.final_answer = "I could not find the file secret.txt."

    # 2. Mock the LLM to return a specific reflection JSON
    mock_llm = MagicMock()
    mock_llm.generate.return_value = """
    ```json
    {
        "success": false,
        "rating": 3,
        "mistakes": ["Repeated the same failing action without changing strategy"],
        "lessons": ["If a file is missing, check the directory contents first instead of retrying the same path"],
        "meta_summary": "Agent got stuck in a loop trying to access a missing file."
    }
    ```
    """

    reflector = Reflector(llm=mock_llm)
    
    # 3. Reflect
    reflected_exp = reflector.reflect(exp)

    # 4. Assert
    assert reflected_exp.success is False
    assert reflected_exp.rating == 3
    assert "Repeated the same failing action without changing strategy" in reflected_exp.mistakes
    assert "If a file is missing, check the directory contents first instead of retrying the same path" in reflected_exp.lessons

if __name__ == "__main__":
    pytest.main([__file__])
