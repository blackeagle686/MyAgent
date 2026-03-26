import logging
import json
import sys
import io
from typing import Optional, Any, Callable
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.status import Status
from rich import box
from rich.rule import Rule

from .agent_planner import Planner
from .agent_memory import Experience
from ..services.llm_service import client

logger = logging.getLogger(__name__)
console = Console()

def agent_loop(agent, user_prompt: str, max_steps: int = 10, ui_callback: Optional[callable] = None) -> str:
    """
    Executes a modular Reason & Act loop with optional UI callback and self-reflection retry.
    """
    def _notify_ui(event_type: str, data: dict):
        if ui_callback:
            ui_callback(event_type, data)

    _notify_ui("start", {"prompt": user_prompt})
    console.print(Panel(f"[bold blue]User Request:[/bold blue] {user_prompt}", box=box.ROUNDED))

    max_attempts = 2
    task_prompt = user_prompt
    
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            console.print(Rule(f"Self-Correction Retry {attempt}/{max_attempts}", style="bold yellow"))
            # Injected lessons from the previous failed attempt
            failed_lessons = ", ".join(exp.lessons) if (locals().get('exp') and exp.lessons) else "Avoid hallucinating data."
            task_prompt = f"{user_prompt}\n\n[SYSTEM REFRESH]: Your previous attempt did not meet quality standards. LESSONS LEARNED: {failed_lessons}. Please retry now, focusing on using REAL evidence from tool outputs."

        # 1. Initialization for this attempt
        agent.task_manager.clear()
        exp = Experience(task_prompt=task_prompt)
        
        try:
            # 2. Decomposition
            with console.status(f"[bold green]Agent is thinking (Attempt {attempt})...") as status:
                analysis, tasks = agent.thinker.think(task_prompt, tools=agent.registry._tools)
            
            _notify_ui("analysis", {"analysis": analysis, "tasks": [t.prompt for t in tasks]})
            console.print(Panel(Markdown(f"### Analysis\n{analysis}"), title=f"[bold yellow]Thinker Analysis[/bold yellow]", border_style="yellow"))
            
            task_table = Table(title="[bold cyan]Decomposed Tasks[/bold cyan]", box=box.SIMPLE_HEAD)
            task_table.add_column("Priority", justify="center", style="magenta")
            task_table.add_column("Task Description", style="white")
            for t in tasks:
                task_table.add_row(str(t.priority), t.prompt)
            console.print(task_table)
            
            agent.task_manager.add_many(tasks)
            if not tasks:
                raise ValueError("Thinker failed to decompose the request into actionable tasks. Please check the strategy and retry.")
            
            planner = Planner(task_manager=agent.task_manager, tools=agent.registry._tools, user_context=task_prompt)
            
            # 3. Execution Loop
            step_count = 0
            action_history = []
            while step_count < max_steps:
                # Loop Detection: Check for repetitive actions
                loop_warning = ""
                if len(action_history) >= 2:
                    last_actions = action_history[-3:]
                    if all(a == last_actions[0] for a in last_actions) and len(last_actions) >= 2:
                        loop_warning = f"\n[!] LOOP WARNING: You have tried the same action {len(last_actions)} times with no change. CHANGE STRATEGY NOW."

                with console.status(f"[bold cyan]Planning Step {step_count + 1}...") as status:
                    # Inject loop warning and global history into the specific plan call
                    result = planner.plan_next(hint=loop_warning)
                
                if not result: break
                task, decision = result
                
                if decision["action"] == "update_plan":
                    console.print("[bold yellow]Planner requested a strategic re-analysis...[/bold yellow]")
                    with console.status("[bold green]Re-thinking strategy...") as status:
                        context_for_thinker = f"{task_prompt}\n\nCURRENT PROGRESS:\n{agent.task_manager.get_history_summary()}\n\nFAILURES:\n{agent.task_manager.get_failed_summary()}"
                        new_analysis, new_tasks = agent.thinker.think(context_for_thinker, tools=agent.registry._tools)
                        agent.task_manager.clear()
                        agent.task_manager.add_many(new_tasks)
                        # We don't break the loop, we just continue with the new tasks
                        console.print(Panel(Markdown(f"### New Analysis\n{new_analysis}"), title="[bold yellow]Strategic Re-think[/bold yellow]", border_style="yellow"))
                        continue

                _notify_ui("plan", {"step": step_count + 1, "task": task.prompt, "decision": decision})
                plan_md = f"**Task:** {task.prompt}\n\n**Action:** `{decision['action']}`\n\n**Reasoning:** {decision['reasoning']}"
                if loop_warning: plan_md = f"[bold red]{loop_warning}[/bold red]\n\n" + plan_md

                if decision.get("tool"):
                    plan_md += f"\n\n**Tool:** `{decision['tool']}`"
                    args_display = decision.get("tool_args") or decision.get("tool_input", "")
                    plan_md += f"\n\n**Args:** `{args_display}`"
                console.print(Panel(Markdown(plan_md), title=f"[bold cyan]Step {step_count + 1}: Planning[/bold cyan]", border_style="cyan"))
                
                if decision["action"] == "execute_tool":
                    tool_name = decision.get("tool")
                    tool_args = decision.get("tool_args", {})
                    # Legacy support/mapping logic
                    if not tool_args and "tool_input" in decision:
                        tool_input = decision["tool_input"]
                        if tool_name == "python_repl": tool_args = {"code": tool_input}
                        elif tool_name == "list_dir": tool_args = {"path": tool_input or "."}
                        elif tool_name == "data_analysis": tool_args = {"file_path": tool_input, "task": "eda"}
                        elif tool_name in ["read_file", "fast_answer"]: tool_args = {"path": tool_input} if tool_name == "read_file" else {"query": tool_input}
                        else: tool_args = {"query": tool_input}

                    action_sig = (tool_name, str(tool_args))
                    action_history.append(action_sig)

                    llm_response = json.dumps({"tool": tool_name, "kwargs": tool_args})
                    with console.status(f"[bold magenta]Executing {tool_name}...") as status:
                        observation = agent.act(llm_response)
                    
                    # Evidence & Terminal Graphics Logic
                    display_obs = observation
                    terminal_graphics = []
                    try:
                        obs_data = json.loads(observation)
                        if "summary_evidence" in obs_data:
                            display_obs = f"[bold yellow]EVIDENCE: {obs_data['summary_evidence']}[/bold yellow]\n\n{observation}"
                        if "steps" in obs_data:
                            for s in obs_data["steps"]:
                                if "data" in s and isinstance(s["data"], dict) and "terminal_viz" in s["data"]:
                                    terminal_graphics.append(s["data"]["terminal_viz"])
                    except: pass

                    _notify_ui("observation", {"tool": tool_name, "observation": observation})
                    console.print(Panel(f"[bold white]{display_obs}[/bold white]", title=f"[bold magenta]Observation ({tool_name})[/bold magenta]", border_style="magenta"))
                    for viz in terminal_graphics: console.print(viz)
                    
                    exp.add_step(thought=decision["reasoning"], tool_call=llm_response, observation=observation)
                    
                    if "Error" in observation or "SyntaxError" in observation:
                        agent.task_manager.fail(task.id, observation)
                    else:
                        agent.task_manager.complete(task.id, observation)

                elif decision["action"] == "finish_task":
                    agent.task_manager.complete(task.id, "Task marked as finished.")
                step_count += 1

            # 4. Final Answer
            completed_tasks = agent.task_manager.completed
            if not completed_tasks:
                final_answer = "I could not complete the requested tasks with evidence."
            else:
                summary_input = "\n".join([f"- {t.prompt}: {t.result}" for t in completed_tasks])
                with console.status("[bold green]Generating Final Answer...") as status:
                    final_answer = client.generate(
                        user_prompt=f"The following tasks were completed:\n{summary_input}\n\nBased on these results, provide a final, user-friendly answer to the request: '{user_prompt}'\nSTRICT: Use specific metrics/evidence from the results below. Do not hallucinate.",
                        sys_prompt="You are a helpful assistant. Be concise and cite specific evidence from the task results."
                    )
            
            exp.final_answer = final_answer
            
            # 5. Reflect & Learn
            with console.status("[bold blue]Agent is self-reflecting...") as status:
                agent.reflector.reflect(exp)
            
            success_color = "green" if exp.success else "red"
            console.print(Panel(
                f"[bold {success_color}]Success: {exp.success}[/bold {success_color}]\n"
                f"[bold cyan]Rating: {exp.rating}/10[/bold cyan]\n"
                f"[bold yellow]Lessons:[/bold yellow] {', '.join(exp.lessons) if exp.lessons else 'None'}",
                title="[bold blue]Self-Reflection Result[/bold blue]", border_style="blue"
            ))

            if exp.rating >= 5 or attempt == max_attempts:
                with console.status("[bold blue]Learning and finishing...") as status:
                    agent.learn(exp)
                console.print(Panel(Markdown(final_answer), title="[bold green]Final Answer[/bold green]", border_style="green"))
                return final_answer
            else:
                console.print("[bold red]Rating too low. Retrying task...[/bold red]")
                # We loop back to top
                
        except Exception as e:
            console.print(f"[bold red]Error in Attempt {attempt}:[/bold red] {str(e)}")
            if attempt == max_attempts: return f"Error: {str(e)}"

    return "Max attempts reached without high quality result."