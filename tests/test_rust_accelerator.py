import time
import numpy as np
import torch
import pytest
from core.utils import cosine_similarity, batch_cosine_similarity
from config import Config

def test_single_cosine_similarity_correctness():
    """Verify that Rust similarity matches PyTorch within tolerance."""
    v1 = np.random.rand(1536).astype(np.float32)
    v2 = np.random.rand(1536).astype(np.float32)
    
    # Force Rust OFF
    Config.use_rust_accelerator = False
    sim_torch = cosine_similarity(v1, v2)
    
    # Force Rust ON
    Config.use_rust_accelerator = True
    sim_rust = cosine_similarity(v1, v2)
    
    print(f"\nSingle Similarity - Torch: {sim_torch:.6f}, Rust: {sim_rust:.6f}")
    assert abs(sim_torch - sim_rust) < 1e-5

def test_batch_cosine_similarity_correctness():
    """Verify that batch Rust similarity matches PyTorch."""
    query = np.random.rand(1536).astype(np.float32)
    targets = np.random.rand(100, 1536).astype(np.float32)
    
    Config.use_rust_accelerator = False
    sims_torch = batch_cosine_similarity(query, targets)
    
    Config.use_rust_accelerator = True
    sims_rust = batch_cosine_similarity(query, targets)
    
    np.testing.assert_allclose(sims_torch, sims_rust, atol=1e-5)
    print("\nBatch similarity correctness verified.")

def test_benchmark_performance():
    """Benchmark Rust vs PyTorch for a large batch of vectors."""
    n_targets = 10000
    dim = 1536
    query = np.random.rand(dim).astype(np.float32)
    targets = np.random.rand(n_targets, dim).astype(np.float32)
    
    # Benchmark PyTorch
    Config.use_rust_accelerator = False
    start = time.time()
    for _ in range(10):
        _ = batch_cosine_similarity(query, targets)
    torch_time = (time.time() - start) / 10
    
    # Benchmark Rust
    Config.use_rust_accelerator = True
    start = time.time()
    for _ in range(10):
        _ = batch_cosine_similarity(query, targets)
    rust_time = (time.time() - start) / 10
    
    speedup = torch_time / rust_time
    print(f"\nBenchmark Results ({n_targets} vectors, {dim} dims):")
    print(f"  PyTorch Avg: {torch_time:.4f}s")
    print(f"  Rust Avg:    {rust_time:.4f}s")
    print(f"  Speedup:     {speedup:.2f}x")
    
    assert rust_time < torch_time, "Rust should be faster for large batches!"

def test_rust_tokenizer():
    """Verify that Rust tokenizer can count tokens."""
    from core.services.llm_service import client
    text = "This is a test of the emergency broadcast system."
    count = client.count_tokens(text)
    print(f"\nTokenizer count for '{text}': {count}")
    assert count > 0

def test_embedding_cache():
    """Verify that EmbeddingCache stores and retrieves vectors."""
    from core.utils import _rust_cache
    if not _rust_cache:
        pytest.skip("Rust cache not available")
    
    key = "test_key"
    vec = [0.1, 0.2, 0.3]
    _rust_cache.set(key, vec)
    retrieved = _rust_cache.get(key)
    assert retrieved == pytest.approx(vec)
    print("\nEmbedding cache verified.")

def test_rank_top_k():
    """Verify that rank_top_k returns correct indices and scores."""
    from core.utils import _rust_engine
    if not _rust_engine:
        pytest.skip("Rust engine not available")
        
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    targets = np.array([
        [1.0, 0.0, 0.0], # exact match
        [0.0, 1.0, 0.0], # orthogonal
        [0.9, 0.1, 0.0], # near match
    ], dtype=np.float32)
    
    ranked = _rust_engine.rank_top_k(query, targets, 2)
    assert ranked[0][0] == 0 # First should be index 0
    assert ranked[1][0] == 2 # Second should be index 2
    print(f"\nRanked indices: {ranked}")

if __name__ == "__main__":
    pytest.main([__file__])
