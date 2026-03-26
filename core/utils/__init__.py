import torch
import torch.nn.functional as F
import numpy as np
from typing import Union, List
# Fix absolute import if needed, but since it's inside core/utils, we use relative or look at config
try:
    from ...config import Config
except:
    try:
        from config import Config
    except:
        Config = None

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

# Import our new robust JSON parser
from .json_utils import parse_robust_json

def cosine_similarity(
    v1: Union[torch.Tensor, list, np.ndarray],
    v2: Union[torch.Tensor, list, np.ndarray]
) -> float:
    # Use Rust if enabled and available
    if Config and Config.use_rust_accelerator and _rust_engine is not None:
        if not isinstance(v1, np.ndarray):
            v1 = np.array(v1, dtype=np.float32)
        if not isinstance(v2, np.ndarray):
            v2 = np.array(v2, dtype=np.float32)
        res = _rust_engine.batch_cosine_similarity(v1.flatten(), v2.reshape(1, -1))
        return float(res[0])

    # Fallback to PyTorch
    if not isinstance(v1, torch.Tensor):
        v1 = torch.tensor(v1)
    if not isinstance(v2, torch.Tensor):
        v2 = torch.tensor(v2)

    v1 = v1.flatten().float()
    v2 = v2.flatten().float()

    return F.cosine_similarity(v1, v2, dim=0).item()

def batch_cosine_similarity(
    query: Union[torch.Tensor, list, np.ndarray],
    targets: Union[torch.Tensor, list, np.ndarray]
) -> np.ndarray:
    if Config and Config.use_rust_accelerator and _rust_engine is not None:
        if not isinstance(query, np.ndarray):
            query = np.array(query, dtype=np.float32)
        if not isinstance(targets, np.ndarray):
            targets = np.array(targets, dtype=np.float32)
        return _rust_engine.batch_cosine_similarity(query.flatten(), targets)

    if not isinstance(query, torch.Tensor):
        query = torch.tensor(query).float()
    if not isinstance(targets, torch.Tensor):
        targets = torch.tensor(targets).float()
    
    return F.cosine_similarity(query.unsqueeze(0), targets, dim=1).numpy()
