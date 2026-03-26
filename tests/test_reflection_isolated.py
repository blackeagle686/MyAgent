import pytest
import json
from unittest.mock import MagicMock

# Mocking the classes instead of importing them to avoid heavy deps
class MockTrajectoryStep:
    def __init__(self, thought, tool_call, observation):
        self.thought = thought
        self.tool_call = tool_call
        self.observation = observation
    def __str__(self):
        return f"Thought: {self.thought}\nTool: {self.tool_call}\nObs: {self.observation}"

class MockExperience:
    def __init__(self):
        self.task_prompt = ""
        self.final_answer = ""
        self.trajectory = []
        self.success = True
        self.rating = 10
        self.mistakes = []
        self.lessons = []
    def add_step(self, thought, tool_call, observation):
        self.trajectory.append(MockTrajectoryStep(thought, tool_call, observation))

# Now import the Reflector, but we need to mock its dependencies too
import sys
from unittest.mock import patch

def test_reflection_logic_isolated():
    # Setup
    with patch('core.agent.agent_reflection.client') as mock_llm:
        from core.agent.agent_reflection import Reflector
        
        exp = MockExperience()
        exp.task_prompt = "Read secret.txt"
        exp.add_step("Try read", "read_file secret.txt", "Error: Not found")
        exp.final_answer = "Failed to find file."

        mock_llm.generate.return_value = json.dumps({
            "success": False,
            "rating": 2,
            "mistakes": ["File was missing"],
            "lessons": ["Check if file exists"],
            "meta_summary": "Bad"
        })

        reflector = Reflector(llm=mock_llm)
        reflected_exp = reflector.reflect(exp)

        assert reflected_exp.success is False
        assert reflected_exp.rating == 2
        assert reflected_exp.lessons == ["Check if file exists"]

if __name__ == "__main__":
    test_reflection_logic_isolated()
    print("Isolated test passed!")
