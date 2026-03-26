import json
import logging
from typing import Optional
from .agent_memory import Experience
from ..services.llm_service import client

logger = logging.getLogger(__name__)

REFLECTION_SYS_PROMPT = """
You are the "Self-Reflection Module" of an autonomous AI agent. 
Your job is to analyze the agent's performance after it completes a task.

Analyze the provided task trajectory (steps taken, tools used, observations) and the final answer.
Be critical. Identify where the agent was inefficient, when it made mistakes, or if it failed the user.

Return your analysis in EXACTLY this JSON format:
{
    "success": true/false,
    "rating": 1-10,
    "mistakes": ["mistake 1", "mistake 2"],
    "lessons": ["actionable lesson 1", "actionable lesson 2"],
    "meta_summary": "Short summary of performance"
}

A "lesson" should be specific advice for the agent's future self to avoid repeating a mistake or to improve efficiency.
"""

class Reflector:
    def __init__(self, llm=client):
        self.llm = llm

    def reflect(self, exp: Experience) -> Experience:
        """
        Analyzes the experience and populates reflection fields.
        """
        if not exp.trajectory:
            logger.warning("Reflection skipped: No trajectory found in experience.")
            return exp

        steps_text = "\n\n".join(
            f"Step {i + 1}:\n{step}" for i, step in enumerate(exp.trajectory)
        )
        
        analysis_input = (
            f"Original Task: {exp.task_prompt}\n\n"
            f"Trajectory:\n{steps_text}\n\n"
            f"Final Answer: {exp.final_answer}"
        )

        try:
            response = self.llm.generate(
                user_prompt=analysis_input,
                sys_prompt=REFLECTION_SYS_PROMPT,
                temperature=0.1 # Low temperature for consistent analysis
            )
            
            # Extract JSON from response (handling potential markdown wrapping)
            json_str = response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
                
            data = json.loads(json_str)
            
            exp.success = data.get("success", True)
            exp.rating = data.get("rating", 10)
            exp.mistakes = data.get("mistakes", [])
            exp.lessons = data.get("lessons", [])
            
            logger.info(f"Reflection completed. Success: {exp.success}, Rating: {exp.rating}/10")
            
        except Exception as e:
            logger.error(f"Error during agent reflection: {e}")
            # Fallback to defaults if reflection fails
            
        return exp
