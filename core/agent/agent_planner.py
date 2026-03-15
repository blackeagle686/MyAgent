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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _parse_json(text: str, fallback: Any) -> Any:
    """Parse JSON from *text*, returning *fallback* on failure."""
    try:
        return json.loads(text)
    except Exception as exc:
        logger.error("JSON parse error: %s", exc)
        return fallback


# ---------------------------------------------------------------------------
# Thinker
# ---------------------------------------------------------------------------

_ANALYSIS_PROMPT = """\
Analyse the problem and return ONLY a plain-text response with these fields:

problem_type:
difficulty:
needs_tools:
strategy:

Available tools for decomposition:
{tool_info}
"""

_TASK_DECOMP_PROMPT = """\
Break the problem into atomic, independently executable tasks.
Return STRICT JSON — no prose, no markdown fences:

[
  {"task": "<description>", "priority": <1-5>}
]
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
        
        analysis = self._analyze(prompt, tool_info)
        tasks = self._decompose(analysis)
        return analysis, tasks

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _analyze(self, prompt: str, tool_info: str = "") -> str:
        sys_prompt = _ANALYSIS_PROMPT.format(tool_info=tool_info)
        return self.model.generate(user_prompt=prompt, sys_prompt=sys_prompt)

    def _decompose(self, analysis: str) -> List[Task]:
        raw = self.model.generate(user_prompt=analysis, sys_prompt=_TASK_DECOMP_PROMPT)
        items = _parse_json(raw, fallback=[])
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

Possible actions:
  execute_tool      — run a tool to make progress
  finish_task       — the task is complete
  retry             — retry the last step
  need_more_thinking — the task needs further analysis

Return STRICT JSON — no prose, no markdown fences:
{
  "action":     "<action>",
  "tool":       "<tool name or null>",
  "tool_input": "<input string>",
  "reasoning":  "<brief explanation>",
  "confidence": <0.0 – 1.0>
}
"""

_PLAN_FALLBACK: Dict[str, Any] = {
    "action": "need_more_thinking",
    "tool": None,
    "tool_input": "",
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

    def plan_next(self) -> Optional[Tuple[Task, Dict[str, Any]]]:
        """Pop the next task and return (task, decision), or None if queue empty."""
        task = self.task_manager.next_task()
        if task is None:
            return None

        decision = self._plan(task)
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
        
        ctx += (
            f"Current sub-task:\n{task.prompt}\n\n"
            f"Status:        {task.status}\n"
            f"Previous result: {task.result}\n"
            f"Assigned tool: {task.tool}\n\n"
            f"Available tools:\n{self._tool_descriptions()}"
        )
        return ctx

    def _plan(self, task: Task) -> Dict[str, Any]:
        context = self._build_context(task)
        raw = self.model.generate(user_prompt=context, sys_prompt=_PLANNER_SYSTEM)
        return _parse_json(raw, fallback=_PLAN_FALLBACK)

    @staticmethod
    def _apply_decision(task: Task, decision: Dict[str, Any]) -> None:
        """Write planner decision back onto the task in-place."""
        if tool := decision.get("tool"):
            task.tool = tool
        if tool_input := decision.get("tool_input"):
            task.tool_input = tool_input