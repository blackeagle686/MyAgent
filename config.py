from dataclasses import dataclass

@dataclass
class Config:
    # OpenRouter API config
    # api_key: str = "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"
    api_key: str = "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"
    base_url: str = "https://openrouter.ai/api/v1"
    
    # LLMs  
    embedding_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    search_model: str = "nousresearch/hermes-3-llama-3.1-405b:free"
    # model: str = "qwen/qwen3-vl-30b-a3b-thinking"
    # model: str = "z-ai/glm-4.5-air:free"
    # model : str = "google/gemini-2.0-flash-lite-preview-02-05:free"
    
    #  model -> for thinking and planning 
    # coder_model -> for coding and heavy code tasks
    # vdb_model -> for vector database operations and embbedings 
    model : str = "nvidia/nemotron-3-super-120b-a12b:free"
    coder_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    vdb_model: str = "all-MiniLM-L6-v2"
    
    # Local LLMs
    local_thinker_model: str = "Qwen/Qwen2.5-3B-Instruct"
    local_planner_model: str = "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Agent config
    top_k: int = 3
    similarity_threshold: float = 0.55
    max_memory_cells: int = 1000
    experience_reward_decay: float = 0.9
    enable_emotions: bool = True
    
    # Rate Limit & Caching
    enable_cache: bool = True
    max_retries: int = 3
    backoff_factor: float = 2.0
    
    # Rust Accelerator
    use_rust_accelerator: bool = True
    