import logging
from .agent_planner import Exp

logger = logging.getLogger(__name__)

def agent_loop(agent, user_prompt: str, max_steps: int = 5) -> str:
    """
    Executes a Reason & Act (ReAct) loop for the agent to approach a problem.
    """
    exp = Exp()
    exp.task_prompt = user_prompt
    
    final_answer = None
    
    for step in range(max_steps):
        logger.info(f"--- Step {step + 1} ---")
        
        # 1. Think & Plan Next Action
        thought_and_action = agent.think(user_prompt, trajectory=exp.trajectory)
        logger.info(f"Thought: {thought_and_action}")
        
        # 2. Check for completion
        if "FINAL_ANSWER:" in thought_and_action:
            final_answer = thought_and_action.split("FINAL_ANSWER:", 1)[1].strip()
            exp.final_answer = final_answer
            break
            
        # 3. Act
        observation = agent.act(thought_and_action)
        logger.info(f"Observation: {observation}")
        
        # 4. Record
        exp.add_step(
            thought="Parsed by agent", # Simplified tracking
            tool_call=thought_and_action, 
            observation=observation
        )

    if final_answer is None:
        final_answer = "Error: Maximum steps reached without a final answer."
        exp.final_answer = final_answer
        
    # 5. Learn (Save experience to database)
    agent.learn(exp)
    
    return final_answer