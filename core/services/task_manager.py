"""
task_manager.py
===============
Task  — a single unit of work with status, priority, and dependency tracking.
TaskManager — thread-safe registry: add, query, advance, and summarise tasks.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Status enum — eliminates bare string literals scattered across the codebase
class TaskStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"


# Task dataclass
@dataclass
class Task:
    prompt: str
    priority: int = 0
    id: str                  = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus       = TaskStatus.PENDING
    result: str              = ""
    tool: str                = ""
    tool_input: str          = ""
    depends_on: List[str]    = field(default_factory=list)
    retry_count: int         = 0
    max_retries: int         = 3
    logs: List[str]          = field(default_factory=list)

    # Convenience
    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

# TaskManager
class TaskManager:
    """Thread-safe task registry with priority + dependency scheduling."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        
    # Adding tasks
    def add(self, task: Task) -> None:
        with self._lock:
            self._tasks[task.id] = task

    def add_many(self, tasks: List[Task]) -> None:
        with self._lock:
            for task in tasks:
                self._tasks[task.id] = task

    def clear(self) -> None:
        """Clears all tasks from the registry."""
        with self._lock:
            self._tasks.clear()

    # Querying
    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == status]

    @property
    def pending(self)   -> List[Task]: return self.by_status(TaskStatus.PENDING)
    @property
    def running(self)   -> List[Task]: return self.by_status(TaskStatus.RUNNING)
    @property
    def completed(self) -> List[Task]: return self.by_status(TaskStatus.DONE)
    @property
    def failed(self)    -> List[Task]: return self.by_status(TaskStatus.FAILED)

    # Scheduling
    def next_task(self) -> Optional[Task]:
        """Return the highest-priority pending task whose dependencies are met."""
        with self._lock:
            available = [
                t for t in self._tasks.values()
                if t.status == TaskStatus.PENDING
                and self._deps_satisfied(t)
            ]
        if not available:
            return None
        return max(available, key=lambda t: t.priority)

    def _deps_satisfied(self, task: Task) -> bool:
        return all(
            (dep_id := dep) in self._tasks
            and self._tasks[dep_id].status == TaskStatus.DONE
            for dep in task.depends_on
        )

    # State transitions
    def start(self, task_id: str) -> None:
        self._set_status(task_id, TaskStatus.RUNNING)

    def complete(self, task_id: str, result: str) -> None:
        self._update(task_id, status=TaskStatus.DONE, result=result)

    def fail(self, task_id: str, error: str) -> None:
        self._update(task_id, status=TaskStatus.FAILED, result=error)

    def _set_status(self, task_id: str, status: TaskStatus) -> None:
        if task := self._tasks.get(task_id):
            task.status = status

    def _update(self, task_id: str, **kwargs) -> None:
        if task := self._tasks.get(task_id):
            for k, v in kwargs.items():
                setattr(task, k, v)

    # History and Progress
    def get_history_summary(self) -> str:
        """Returns a compact string of all completed actions and results."""
        with self._lock:
            done = [t for t in self._tasks.values() if t.status == TaskStatus.DONE]
            if not done:
                return "No tasks completed yet."
            return "\n".join([f"- [COMPLETED] {t.prompt} -> Result: {str(t.result)[:100]}..." for t in done])

    def get_failed_summary(self) -> str:
        """Returns a summary of failed tasks and their errors."""
        with self._lock:
            failed = [t for t in self._tasks.values() if t.status == TaskStatus.FAILED]
            if not failed:
                return "No failures recorded."
            return "\n".join([f"- [FAILED] {t.prompt} -> Error: {t.result}" for t in failed])

    # Summary
    def summary(self) -> Dict[str, int]:
        return {
            "total":   len(self._tasks),
            "pending": len(self.pending),
            "running": len(self.running),
            "done":    len(self.completed),
            "failed":  len(self.failed),    
        }