"""
memory_manager.py
=================
MemoryManager — unified service layer over all memory subsystems.

    ┌─────────────────────────────────────────┐
    │              MemoryManager              │
    │                                         │
    │  MemoryStore      (semantic / long-term)│
    │  ExperienceMemory (episodic / history)  │
    └─────────────────────────────────────────┘

Usage pattern (memory feeds reasoning, not just context):
    ctx  = manager.context_for(query)       # → reasoning input
    exps = manager.past_experiences(query)  # → planning input
    manager.remember(content, metadata)     # → store new fact
    manager.record(experience)              # → store trajectory
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.agent_memory import (
    Experience,
    ExperienceMemory,
    ExperienceMemoryConfig,
    MemoryStore,
    MemoryStoreConfig,
    TrajectoryStep,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class MemoryManagerConfig:
    semantic: MemoryStoreConfig      = field(default_factory=MemoryStoreConfig)
    episodic: ExperienceMemoryConfig = field(default_factory=ExperienceMemoryConfig)
    default_top_k: int               = 3


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------

class MemoryManager:
    """
    Single entry-point for all agent memory operations.

    Subsystems
    ----------
    semantic  — MemoryStore:      facts, observations, tool outputs
    episodic  — ExperienceMemory: full task trajectories + lessons
    """

    def __init__(self, cfg: Optional[MemoryManagerConfig] = None) -> None:
        self.cfg      = cfg or MemoryManagerConfig()
        self.semantic = MemoryStore(cfg=self.cfg.semantic)
        self.episodic = ExperienceMemory(cfg=self.cfg.episodic)

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a new fact / observation in semantic memory.
        Returns the memory cell id.
        """
        cell_id = self.semantic.add(content, metadata)
        logger.debug("Stored semantic memory: %s", cell_id)
        return cell_id

    def record(self, experience: Experience) -> None:
        """Persist a completed task trajectory to episodic memory."""
        self.episodic.add(experience)
        logger.debug("Recorded experience: %s", experience.id)

    # ------------------------------------------------------------------
    # Read API  (feed these directly into reasoning / planning)
    # ------------------------------------------------------------------

    def recall(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant semantic memories for *query*.
        Each item: {"summary", "content", "metadata"}
        """
        return self.semantic.retrieve(query, top_k or self.cfg.default_top_k)

    def past_experiences(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve past task trajectories relevant to *query*.
        Each item: {"summary", "task_prompt", "final_answer"}
        """
        return self.episodic.retrieve(query, top_k or self.cfg.default_top_k)

    def context_for(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> str:
        """
        Return a single string of the most relevant semantic memories.
        Drop this directly into a reasoning / planning prompt.
        """
        return self.semantic.retrieve_context(query, top_k or self.cfg.default_top_k)

    # ------------------------------------------------------------------
    # Compound helper  (reasoning input = facts + past lessons)
    # ------------------------------------------------------------------

    def reasoning_input(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> str:
        """
        Combine semantic context and episodic lessons into one block
        ready to be injected into an LLM reasoning prompt.

        Format:
            ## Relevant Knowledge
            <semantic memories>

            ## Past Experience
            <episodic summaries>
        """
        k = top_k or self.cfg.default_top_k

        semantic_ctx = self.context_for(query, k)
        episodes     = self.past_experiences(query, k)

        episode_text = "\n".join(
            f"- [{e.get('task_prompt', '')}] → {e.get('summary', '')}"
            for e in episodes
        )

        parts = []
        if semantic_ctx:
            parts.append(f"## Relevant Knowledge\n{semantic_ctx}")
        if episode_text:
            parts.append(f"## Past Experience\n{episode_text}")

        return "\n\n".join(parts) if parts else ""

    # ------------------------------------------------------------------
    # Experience builder  (convenience — avoids importing TrajectoryStep)
    # ------------------------------------------------------------------

    @staticmethod
    def new_experience(
        task_prompt: str,
        final_answer: Optional[str] = None,
    ) -> Experience:
        """Create a fresh Experience ready to receive steps."""
        return Experience(task_prompt=task_prompt, final_answer=final_answer)

    @staticmethod
    def add_step(
        exp: Experience,
        thought: str,
        tool_call: str,
        observation: str,
    ) -> None:
        """Append one trajectory step to *exp*."""
        exp.add_step(thought=thought, tool_call=tool_call, observation=observation)