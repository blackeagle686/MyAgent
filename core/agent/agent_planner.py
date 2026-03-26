"""
Thinker & Planner
=================
Thinker  — analyses a problem and decomposes it into atomic tasks.
Planner  — decides the next best action for each task.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..services.llm_service import client
from ..services.task_manager import Task, TaskManager
from ..utils.json_utils import parse_robust_json

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Thinker
# ---------------------------------------------------------------------------

_ANALYSIS_PROMPT = """\
You are an expert systems analyst. Analyze the user's request and provide a technical strategy.

CRITICAL: Do NOT invent, simulate, or assume any tool outputs. 
You do NOT know the content of any file unless it was provided in the history.
STRICTLY follow these fields:

problem_type: (e.g., Coding, System, Research)
difficulty: (1-10)
needs_tools: (Yes/No)
strategy: (Detailed step-by-step approach. DO NOT include predicted tool outputs.)

Available tools for context:
{tool_info}
"""

_TASK_DECOMP_PROMPT = """\
You are a project manager. Based on the analysis provided, decompose the project into a list of atomic, sequential tasks.

STRICT RULES:
1. Return ONLY a valid JSON array of objects.
2. Each task must be a single tool call or a simple logical step.
3. DO NOT include predicted observations.
4. DO NOT include prose or markdown fences.

Example Format:
[
  {"task": "Read requirements.txt", "priority": 5},
  {"task": "Install dependencies", "priority": 4}
]

Analysis to decompose:
"""


class Thinker:
    """Analyses a problem and decomposes it into a prioritised task list."""

    def __init__(self) -> None:
        self.model = client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def think(self, prompt: str, tools: Optional[Dict[str, Any]] = None) -> Tuple[str, List[Task]]:
        """Return (analysis_text, tasks) for *prompt*."""
        tool_info = ""
        if tools:
            tool_info = "\n".join([f"- {name}: {tool.description}" for name, tool in tools.items()])
        
        # Determine which model to use for analysis/decomposition
        target_model = None
        coding_keywords = ["python", "script", "code", "function", "class", "coding", "logic", "algorithm"]
        if any(kw in prompt.lower() for kw in coding_keywords):
            target_model = getattr(self.model, "coder_model", None)
            if target_model:
                logger.info("Thinker switching to coder_model for coding prompt")

        analysis = self._analyze(prompt, tool_info, model_override=target_model)
        tasks = self._decompose(analysis, model_override=target_model)
        return analysis, tasks

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _analyze(self, prompt: str, tool_info: str = "", model_override: Optional[str] = None) -> str:
        sys_prompt = _ANALYSIS_PROMPT.format(tool_info=tool_info)
        return self.model.generate(user_prompt=prompt, sys_prompt=sys_prompt, model=model_override)

    def _decompose(self, analysis: str, model_override: Optional[str] = None) -> List[Task]:
        raw = self.model.generate(user_prompt=analysis, sys_prompt=_TASK_DECOMP_PROMPT, model=model_override)
        logger.info("DECOMPOSE RAW: %s", raw)
        items = parse_robust_json(raw, fallback=[])
        return [
            Task(prompt=item["task"], priority=item["priority"])
            for item in items
            if "task" in item and "priority" in item
        ]


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

_PLANNER_SYSTEM = """\
You are an autonomous AI planner. Decide the next best action for the current task.

CRITICAL RULES:
1. PROGRESS AWARENESS: Review the "GLOBAL HISTORY" carefully. If a fact was already established (e.g. file exists), DO NOT repeat the check.
2. NO REPETITION: Never call the same tool with the same arguments if the previous result was conclusive or an error.
3. ERROR RECOVERY: If a tool failed (e.g. SyntaxError), your next action MUST be to FIX the error (e.g. rewrite code) or change strategy.
4. STRATEGIC SHIFT: If you realize the current set of tasks is wrong or a dead-end, use the 'update_plan' action.

Possible actions:
  execute_tool      — run a tool to make progress
  finish_task       — the task is complete
  retry             — retry the last step
  update_plan       — current tasks are invalid; request a re-think
  need_more_thinking — the task needs further analysis

Return STRICT JSON:
{
  "action":     "<action>",
  "tool":       "<tool name or null>",
  "tool_args":  {"arg_name": "value"},
  "reasoning":  "<brief explanation of why this step is PROGRESS, not repetition>",
  "confidence": <0.0 – 1.0>
}
"""

_PLAN_FALLBACK: Dict[str, Any] = {
    "action": "need_more_thinking",
    "tool": None,
    "tool_args": {},
    "reasoning": "parse failure",
    "confidence": 0.2,
}


@dataclass
class PlannerConfig:
    """Tunable knobs for Planner — keeps __init__ clean."""
    tool_description_separator: str = "\n"


class Planner:
    """Decides the next best action for each queued task."""

    def __init__(
        self,
        task_manager: TaskManager,
        tools: Dict[str, Any],
        user_context: Optional[str] = None,
        cfg: Optional[PlannerConfig] = None,
    ) -> None:
        self.model = client
        self.task_manager = task_manager
        self.tools = tools
        self.user_context = user_context
        self.cfg = cfg or PlannerConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan_next(self, hint: Optional[str] = None) -> Optional[Tuple[Task, Dict[str, Any]]]:
        """Pop the next task and return (task, decision), or None if queue empty."""
        task = self.task_manager.next_task()
        if task is None:
            return None

        decision = self._plan(task, hint=hint)
        self._apply_decision(task, decision)
        return task, decision

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tool_descriptions(self) -> str:
        lines = [
            f"{name}: {tool.description}"
            for name, tool in self.tools.items()
        ]
        return self.cfg.tool_description_separator.join(lines)

    def _build_context(self, task: Task) -> str:
        ctx = ""
        if self.user_context:
            ctx += f"Original User Goal: {self.user_context}\n\n"
        
        ctx += "--- GLOBAL HISTORY (What we already did) ---\n"
        ctx += self.task_manager.get_history_summary() + "\n"
        ctx += "\n--- PREVIOUS FAILURES (Avoid these) ---\n"
        ctx += self.task_manager.get_failed_summary() + "\n\n"

        ctx += (
            f"Current sub-task: {task.prompt}\n"
            f"Previous result for THIS task: {task.result}\n"
            f"Available tools:\n{self._tool_descriptions()}"
        )
        return ctx

    def _plan(self, task: Task, hint: Optional[str] = None) -> Dict[str, Any]:
        context = self._build_context(task)
        if hint:
            context = f"!!! WARNING/HINT !!!\n{hint}\n\n" + context
        
        # Determine which model to use
        target_model = None
        coding_keywords = ["python", "script", "code", "function", "class", "coding", "logic", "algorithm"]
        task_text = (task.prompt + " " + (self.user_context or "")).lower()
        
        if any(kw in task_text for kw in coding_keywords):
            target_model = getattr(self.model, "coder_model", None)
            if target_model:
                # logger.info("Using coder_model")
                pass
        
        raw = self.model.generate(user_prompt=context, sys_prompt=_PLANNER_SYSTEM, model=target_model)
        if raw == "LLM generation failed":
            logger.error("Planner generation failed")
            return _PLAN_FALLBACK
        
        logger.info("PLAN RAW: %s", raw)
        return parse_robust_json(raw, fallback=_PLAN_FALLBACK)

    @staticmethod
    def _apply_decision(task: Task, decision: Dict[str, Any]) -> None:
        """Write planner decision back onto the task in-place."""
        if tool := decision.get("tool"):
            task.tool = tool
        if tool_args := decision.get("tool_args"):
            task.tool_input = tool_args  # Keep using tool_input internally but store dict