import torch
import torch.nn.functional as F
import numpy as np
from typing import Union, List
from config import Config

# Attempt to import Rust accelerator
try:
    from rust_accelerator import (
        FastVectorEngine,
        RustTokenizer,
        EmbeddingCache,
        ParallelOrchestrator
    )
    _rust_engine = FastVectorEngine()
    _rust_cache = EmbeddingCache()
    _rust_orchestrator = ParallelOrchestrator()
except ImportError:
    _rust_engine = None
    _rust_cache = None
    _rust_orchestrator = None


def cosine_similarity(
    v1: Union[torch.Tensor, list, np.ndarray],
    v2: Union[torch.Tensor, list, np.ndarray]
) -> float:
    # Use Rust if enabled and available
    if Config.use_rust_accelerator and _rust_engine is not None:
        # FastVectorEngine expects numpy arrays for zero-copy
        if not isinstance(v1, np.ndarray):
            v1 = np.array(v1, dtype=np.float32)
        if not isinstance(v2, np.ndarray):
            v2 = np.array(v2, dtype=np.float32)
        
        # We can use the batch function for a single pair by wrapping v2 in a matrix
        res = _rust_engine.batch_cosine_similarity(v1.flatten(), v2.reshape(1, -1))
        return float(res[0])

    # Fallback to PyTorch
    if not isinstance(v1, torch.Tensor):
        v1 = torch.tensor(v1)

    if not isinstance(v2, torch.Tensor):
        v2 = torch.tensor(v2)

    v1 = v1.flatten().float()
    v2 = v2.flatten().float()

    return F.cosine_similarity(
        v1,
        v2,
        dim=0
    ).item()


def batch_cosine_similarity(
    query: Union[torch.Tensor, list, np.ndarray],
    targets: Union[torch.Tensor, list, np.ndarray]
) -> np.ndarray:
    """
    Computes cosine similarity between a single query vector and a batch of target vectors.
    Returns a numpy array of similarities.
    """
    if Config.use_rust_accelerator and _rust_engine is not None:
        if not isinstance(query, np.ndarray):
            query = np.array(query, dtype=np.float32)
        if not isinstance(targets, np.ndarray):
            targets = np.array(targets, dtype=np.float32)
        
        return _rust_engine.batch_cosine_similarity(query.flatten(), targets)

    # Fallback/Default implementation (simplified for brevity, can be optimized further if needed)
    # If not using Rust, we just loop or use torch if available
    if not isinstance(query, torch.Tensor):
        query = torch.tensor(query).float()
    if not isinstance(targets, torch.Tensor):
        targets = torch.tensor(targets).float()
    
    # torch's cosine_similarity supports broadcasting
    return F.cosine_similarity(query.unsqueeze(0), targets, dim=1).numpy()