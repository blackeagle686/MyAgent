import logging
import json
import sys
from typing import Optional, Any, Callable
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.status import Status
from rich import box

from .agent_planner import Planner
from .agent_memory import Experience
from ..services.llm_service import client

logger = logging.getLogger(__name__)
console = Console()

def agent_loop(agent, user_prompt: str, max_steps: int = 10, ui_callback: Optional[callable] = None) -> str:
    """
    Executes a modular Reason & Act loop with optional UI callback.
    ui_callback signature: (event_type: str, data: dict)
    """
    def _notify_ui(event_type: str, data: dict):
        if ui_callback:
            ui_callback(event_type, data)

    _notify_ui("start", {"prompt": user_prompt})
    console.print(Panel(f"[bold blue]User Request:[/bold blue] {user_prompt}", box=box.ROUNDED))

    # 1. Decomposition
    try:
        with console.status("[bold green]Agent is thinking (Analyzing & Decomposing)...") as status:
            analysis, tasks = agent.thinker.think(user_prompt, tools=agent.registry._tools)
        
        _notify_ui("analysis", {"analysis": analysis, "tasks": [t.prompt for t in tasks]})
        console.print(Panel(Markdown(f"### Analysis\n{analysis}"), title="[bold yellow]Thinker Analysis[/bold yellow]", border_style="yellow"))
        
        task_table = Table(title="[bold cyan]Decomposed Tasks[/bold cyan]", box=box.SIMPLE_HEAD)
        task_table.add_column("Priority", justify="center", style="magenta")
        task_table.add_column("Task Description", style="white")
        
        for t in tasks:
            task_table.add_row(str(t.priority), t.prompt)
        
        console.print(task_table)
        
        agent.task_manager.add_many(tasks)
        
        # Initialize Planner
        planner = Planner(
            task_manager=agent.task_manager,
            tools=agent.registry._tools,
            user_context=user_prompt
        )
        
        exp = Experience()
        exp.task_prompt = user_prompt
        
        step_count = 0
        while step_count < max_steps:
            # 2. Planning
            with console.status(f"[bold cyan]Planning Step {step_count + 1}...") as status:
                result = planner.plan_next()
            
            if not result:
                break
                
            task, decision = result
            _notify_ui("plan", {"step": step_count + 1, "task": task.prompt, "decision": decision})
            
            # Display Plan
            plan_md = f"**Task:** {task.prompt}\n\n**Action:** `{decision['action']}`\n\n**Reasoning:** {decision['reasoning']}"
            if decision.get("tool"):
                plan_md += f"\n\n**Tool:** `{decision['tool']}`"
                plan_md += f"\n\n**Input:** `{decision['tool_input']}`"
                
            console.print(Panel(Markdown(plan_md), title=f"[bold cyan]Step {step_count + 1}: Planning[/bold cyan]", border_style="cyan"))
            
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
                elif tool_name == "fast_answer":
                    kwargs = {"query": tool_input}
                else:
                    kwargs = {"query": tool_input}

                llm_response = json.dumps({
                    "tool": tool_name,
                    "kwargs": kwargs
                })
                
                with console.status(f"[bold magenta]Executing {tool_name}...") as status:
                    observation = agent.act(llm_response)
                
                _notify_ui("observation", {"tool": tool_name, "observation": observation})
                console.print(Panel(f"[bold white]{observation}[/bold white]", title=f"[bold magenta]Observation ({tool_name})[/bold magenta]", border_style="magenta"))
                
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
                console.print(f"[bold green]✓ Task Finished:[/bold green] {task.prompt}")
            
            elif decision["action"] == "need_more_thinking":
                console.print(f"[bold yellow]! Need More Thinking:[/bold yellow] {decision['reasoning']}")
                
            step_count += 1

        # 4. Final Answer Generation
        completed_tasks = agent.task_manager.completed
        if not completed_tasks:
            final_answer = "I could not complete the requested tasks."
        else:
            summary_input = "\n".join([f"- {t.prompt}: {t.result}" for t in completed_tasks])
            
            with console.status("[bold green]Generating Final Answer...") as status:
                # Use direct client call with a clear instruction to avoid tool-calling hallucinations
                final_answer = client.generate(
                    user_prompt=f"The following tasks were completed:\n{summary_input}\n\nBased on these results, provide a final, user-friendly answer to the original request: '{user_prompt}'",
                    sys_prompt="You are a helpful assistant. Summarize the findings clearly without mentioning internal tool names."
                )
        
        _notify_ui("final_answer", {"answer": final_answer})
        exp.final_answer = final_answer
        
        # 5. Learn
        with console.status("[bold blue]Agent is learning from experience...") as status:
            agent.learn(exp)
        
        console.print(Panel(Markdown(final_answer), title="[bold green]Final Answer[/bold green]", border_style="green"))
        
        return final_answer

    except Exception as e:
        console.print(f"[bold red]Critical Error in Agent Loop:[/bold red] {str(e)}")
        logger.error(f"Agent loop error: {e}", exc_info=True)
        return f"Error: {str(e)}"