import json
import logging
from typing import Optional
from .agent_memory import Experience
from ..services.llm_service import client
from ..utils.json_utils import parse_robust_json

logger = logging.getLogger(__name__)

REFLECTION_SYS_PROMPT = """
You are the "Self-Reflection Module" of an autonomous AI agent. 
Analyze the task trajectory and final answer critically.

CRITICAL RULES:
1. NO HALLUCINATION: If the final answer contains data (numbers, rows, columns) that NEVER appeared in the trajectory observations, set success=False and rating=1.
2. NO DEFEATISM: If the agent says "I could not complete the task" or "I was unable to...", set success=False and rating=2, UNLESS the trajectory shows it exhausted ALL tools (including reading the file and trying code).
3. EVIDENCE CHECK: For a 10/10 rating, the agent MUST have produced verifiable evidence (e.g., metrics, charts, file contents) and cited them.
4. LESSONS: Provide concrete, actionable lessons to avoid repeating mistakes (e.g., "Use head before pandas", "Check directory first").

Return EXACT JSON:
{
    "success": true/false,
    "rating": 1-10,
    "mistakes": ["list of failures"],
    "lessons": ["specific advice for next time"],
    "meta_summary": "one line summary"
}
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
            
            data = parse_robust_json(response, fallback={})
            
            exp.success = data.get("success", False)
            exp.rating = data.get("rating", 1)
            exp.mistakes = data.get("mistakes", ["Reflection failed or was too lenient"])
            exp.lessons = data.get("lessons", ["Always execute tools to verify claims"])
            
            logger.info(f"Reflection completed. Success: {exp.success}, Rating: {exp.rating}/10")
            
        except Exception as e:
            logger.error(f"Error during agent reflection: {e}")
            # Fallback to defaults if reflection fails
            
        return exp
