"""
Agent Memory System
===================
Architecture:
    MemoryStore      — semantic long-term memory (vector-backed)
    ExperienceMemory — episodic memory (task trajectories)

Design principle:
    Memory must feed → reasoning, planning, and tool selection.
    It is NOT just a context store.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..utils import cosine_similarity
from ..services.vector_db_service import ChromaVectorDB
from ..services.llm_service import client, encoder_client
from config import Config

logger = logging.getLogger(__name__)


# Shared helpers
def _to_vec(encoder, text: str) -> list:
    """Encode *text* and always return a plain Python list."""
    tensor = encoder.encode(text)
    return tensor.tolist() if hasattr(tensor, "tolist") else list(tensor)


def _safe_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten metadata values to types accepted by ChromaDB."""
    return {
        k: v if isinstance(v, (str, int, float, bool)) else json.dumps(v)
        for k, v in meta.items()
    }


def _chroma_rows(results: dict) -> List[Dict[str, Any]]:
    """Unpack a ChromaDB result dict into a flat list of row dicts."""
    if not (results and results.get("documents")):
        return []
    docs = results["documents"][0]
    metas = (results.get("metadatas") or [[]])[0] or [{} for _ in docs]
    return [{"doc": d, "meta": m} for d, m in zip(docs, metas)]


# MemoryCell — a single unit of long-term semantic memory
@dataclass
class MemoryCell:
    content: str
    encoder: Any
    llm: Any
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    # populated by build()
    vec: Optional[list] = field(default=None, init=False)
    summary: Optional[str] = field(default=None, init=False)
    summary_vec: Optional[list] = field(default=None, init=False)
    neighbors: set = field(default_factory=set, init=False)

    def build(self) -> None:
        """Encode content and generate a compact summary."""
        try:
            self.vec = _to_vec(self.encoder, self.content)
            self.summary = self.llm.generate(
                user_prompt=self.content,
                sys_prompt="Summarize in <=100 words",
            )
            self.summary_vec = _to_vec(self.encoder, self.summary)
        except Exception as exc:
            logger.error("MemoryCell.build failed: %s", exc)

    def similarity(self, vec: list) -> float:
        return cosine_similarity(self.vec, vec)


# MemoryStore — semantic long-term memory backed by ChromaDB
@dataclass
class MemoryStoreConfig:
    similarity_threshold: float = Config.similarity_threshold
    collection_name: str = "agent_memory"
    persist_dir: str = "./chroma"
    vdb_model: str = Config.vdb_model


class MemoryStore:
    """
    Persistent semantic memory store.

    Flow:
        add(content) → build MemoryCell → persist to ChromaDB
                      → async link to nearest neighbours
        retrieve(query) → vector search → ranked memory chunks
    """

    def __init__(
        self,
        encoder=encoder_client,
        llm=client,
        cfg: Optional[MemoryStoreConfig] = None,
    ) -> None:
        self.encoder = encoder
        self.llm = llm
        self.cfg = cfg or MemoryStoreConfig()

        self.vector_db = ChromaVectorDB(
            collection_name=self.cfg.collection_name,
            persist_dir=self.cfg.persist_dir,
            model=self.cfg.vdb_model,
        )
        self.cells: Dict[str, MemoryCell] = {}
        self._lock = threading.Lock()
        self._link_queue: queue.Queue = queue.Queue()

        self._worker_thread = threading.Thread(
            target=self._link_worker, daemon=True
        )
        self._worker_thread.start()

    # Public API
    def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Encode, store, and asynchronously link a new memory."""
        cell = MemoryCell(
            content=content,
            encoder=self.encoder,
            llm=self.llm,
            metadata=metadata or {},
        )
        cell.build()

        with self._lock:
            self.cells[cell.id] = cell

        if cell.summary:
            safe_meta = _safe_metadata({**cell.metadata, "content": cell.content})
            self.vector_db.add(
                ids=[cell.id],
                documents=[cell.summary],
                metadatas=[safe_meta],
            )
            self._link_queue.put(cell)

        return cell.id

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Return top-k memory chunks most relevant to *query*."""
        rows = _chroma_rows(self.vector_db.query(query=query, top_k=top_k))
        return [
            {
                "summary": r["doc"],
                "content": r["meta"].get("content", ""),
                "metadata": r["meta"],
            }
            for r in rows
        ]

    def rank_context(self, query_vec: list, candidates: List[MemoryCell], top_k: int = 5) -> List[MemoryCell]:
        """High-speed Rust ranking for re-ranking or filtering memory cells."""
        from ..utils import _rust_engine
        if Config.use_rust_accelerator and _rust_engine:
            import numpy as np
            target_veclist = [c.vec for c in candidates if c.vec is not None]
            if not target_veclist: return []
            
            targets = np.array(target_veclist, dtype=np.float32)
            query = np.array(query_vec, dtype=np.float32)
            
            # Use Rust ranking
            ranked_indices = _rust_engine.rank_top_k(query, targets, top_k)
            return [candidates[idx] for idx, score in ranked_indices]
        
        # Fallback to python sort
        candidates.sort(key=lambda c: c.similarity(query_vec), reverse=True)
        return candidates[:top_k]

    def retrieve_context(self, query: str, top_k: int = 3, max_tokens: int = 2000) -> str:
        """
        Retrieves context and ensures it fits within token limits.
        Prioritizes summaries first to maximize the amount of relevant 
        information included in the budget.
        """
        memories = self.retrieve(query, top_k)
        context_parts = []
        total_tokens = 0
        
        # Phase 1: Try to fit all summaries
        for m in memories:
            summary = m.get("summary")
            if not summary: continue
            
            summary_text = f"[Summary]: {summary}"
            tokens = self.llm.count_tokens(summary_text)
            if total_tokens + tokens <= max_tokens:
                context_parts.append(summary_text)
                total_tokens += tokens
            
        # Phase 2: If budget remains, add raw content for the top matches
        for m in memories:
            content = m.get("content")
            if not content: continue
            
            content_text = f"[Raw Detail]: {content}"
            tokens = self.llm.count_tokens(content_text)
            if total_tokens + tokens <= max_tokens:
                context_parts.append(content_text)
                total_tokens += tokens
            else:
                # Potentially truncate or stop
                break
                
        return "\n\n".join(context_parts)

    # Internal
    def _link_worker(self) -> None:
        """Background thread: link each new cell to its nearest neighbours."""
        while True:
            cell: MemoryCell = self._link_queue.get()
            try:
                rows = _chroma_rows(
                    self.vector_db.query(query=cell.summary, top_k=5)
                )
                with self._lock:
                    for r in rows:
                        neighbour_id = r["meta"].get("id")
                        if neighbour_id and neighbour_id != cell.id:
                            cell.neighbors.add(neighbour_id)
            except Exception as exc:
                logger.error("Link worker error: %s", exc)
            finally:
                self._link_queue.task_done()


# Trajectory step + Experience — episodic memory building blocks
@dataclass
class TrajectoryStep:
    thought: str
    tool_call: str
    observation: str

    def __str__(self) -> str:
        return (
            f"Thought:     {self.thought}\n"
            f"Tool call:   {self.tool_call}\n"
            f"Observation: {self.observation}"
        )


@dataclass
class Experience:
    task_prompt: Optional[str] = None
    final_answer: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trajectory: List[TrajectoryStep] = field(default_factory=list)
    summary: Optional[str] = field(default=None, init=False)
    
    # Reflection fields
    success: bool = field(default=True)
    mistakes: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    rating: int = field(default=10)

    def add_step(self, thought: str, tool_call: str, observation: str) -> None:
        self.trajectory.append(
            TrajectoryStep(thought=thought, tool_call=tool_call, observation=observation)
        )

    def build_summary(self) -> None:
        steps_text = "\n\n".join(
            f"Step {i + 1}:\n{step}" for i, step in enumerate(self.trajectory)
        )
        body = (
            f"Task: {self.task_prompt}\n\n"
            f"Trajectory:\n{steps_text}\n\n"
            f"Final Answer: {self.final_answer}\n\n"
            f"Reflection:\n"
            f"- Success: {self.success}\n"
            f"- Rating: {self.rating}/10\n"
            f"- Mistakes: {', '.join(self.mistakes) if self.mistakes else 'None'}\n"
            f"- Lessons: {', '.join(self.lessons) if self.lessons else 'None'}"
        )
        self.summary = client.generate(
            user_prompt=body,
            sys_prompt="Summarize this agent trajectory, its success/failure, and the key lessons learned for future improvement in <=120 words",
        )


# ExperienceMemory — episodic memory backed by ChromaDB
@dataclass
class ExperienceMemoryConfig:
    collection_name: str = "agent_experiences"
    persist_dir: str = "./chroma"
    vdb_model: str = "all-MiniLM-L6-v2"


class ExperienceMemory:
    """
    Episodic memory: stores summarised task trajectories so past
    experience can inform future planning.
    """

    def __init__(self, cfg: Optional[ExperienceMemoryConfig] = None) -> None:
        self.cfg = cfg or ExperienceMemoryConfig()
        self.vector_db = ChromaVectorDB(
            collection_name=self.cfg.collection_name,
            persist_dir=self.cfg.persist_dir,
            model=self.cfg.vdb_model,
        )

    def add(self, exp: Experience) -> None:
        """Summarise and persist an experience."""
        exp.build_summary()
        if not exp.summary:
            return

        self.vector_db.add(
            ids=[exp.id],
            documents=[exp.summary],
            metadatas=[
                {
                    "task_prompt": str(exp.task_prompt or ""),
                    "final_answer": str(exp.final_answer or ""),
                    "num_steps": len(exp.trajectory),
                }
            ],
        )

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Return past experiences most relevant to *query*."""
        rows = _chroma_rows(self.vector_db.query(query=query, top_k=top_k))
        return [
            {
                "summary": r["doc"],
                "task_prompt": r["meta"].get("task_prompt", ""),
                "final_answer": r["meta"].get("final_answer", ""),
            }
            for r in rows
        ]