import logging
import json
from .agent_planner import Planner
from .agent_memory import Experience

logger = logging.getLogger(__name__)

def agent_loop(agent, user_prompt: str, max_steps: int = 10) -> str:
    """
    Executes a modular Reason & Act loop:
    1. Thinker decomposes the problem.
    2. Planner decides the next step for each task.
    """
    # 1. Decomposition
    logger.info(f"Analyzing user request: {user_prompt}")
    analysis, tasks = agent.thinker.think(user_prompt)
    logger.info(f"Analysis: {analysis}")
    
    agent.task_manager.add_many(tasks)
    
    # Initialize Planner
    planner = Planner(
        task_manager=agent.task_manager,
        tools=agent.registry._tools,
        user_context=user_prompt # Pass original context
    )
    
    exp = Experience()
    exp.task_prompt = user_prompt
    
    step_count = 0
    while step_count < max_steps:
        # 2. Planning
        result = planner.plan_next()
        if not result:
            break
            
        task, decision = result
        logger.info(f"Step {step_count + 1} - Task: {task.prompt}")
        logger.info(f"Decision: {decision['action']} - Reasoning: {decision['reasoning']}")
        
        # 3. Execution
        if decision["action"] == "execute_tool":
            tool_name = decision.get("tool")
            tool_input = decision.get("tool_input")
            
            # Construct a response format that AgentActor expects
            if tool_name == "python_repl":
                kwargs = {"code": tool_input}
            elif tool_name == "list_dir":
                kwargs = {"path": tool_input or "."}
            elif tool_name == "read_file":
                kwargs = {"path": tool_input}
            elif tool_name == "write_file":
                kwargs = {"path": tool_input, "content": ""} # Basic placeholder
            else:
                kwargs = {"query": tool_input}

            llm_response = json.dumps({
                "tool": tool_name,
                "kwargs": kwargs
            })
            
            # For more robust mapping, we might need a translation layer
            # But here we try to execute directly via actor if possible, 
            # or use the registry directly since we have the tool name and input.
            
            observation = agent.act(llm_response)
            logger.info(f"Observation: {observation}")
            
            # Record step in experience
            exp.add_step(
                thought=decision["reasoning"],
                tool_call=llm_response,
                observation=observation
            )
            
            # Update task in manager
            agent.task_manager.complete(task.id, observation)
            
        elif decision["action"] == "finish_task":
            agent.task_manager.complete(task.id, "Task marked as finished by planner.")
        
        elif decision["action"] == "need_more_thinking":
            # Potentially trigger a re-decomposition if needed
            pass
            
        step_count += 1

    # 4. Final Answer Generation
    # For now, we'll use a simple summary of completed tasks as the final answer
    completed_tasks = agent.task_manager.completed
    summary = "\n".join([f"- {t.prompt}: {t.result}" for t in completed_tasks])
    
    final_answer = agent.think(f"Summarize the results of these tasks for the user: {summary}")
    exp.final_answer = final_answer
    
    # 5. Learn
    agent.learn(exp)
    
    return final_answer