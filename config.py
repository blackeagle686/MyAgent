from dataclasses import dataclass

@dataclass
class Config:
    # OpenRouter API config
    api_key: str = "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"
    base_url: str = "https://openrouter.ai/api/v1"
    
    # LLMs
    embedding_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    search_model: str = "nousresearch/hermes-3-llama-3.1-405b:free"
    model: str = "qwen/qwen3-vl-30b-a3b-thinking"
    vdb_model: str = "all-MiniLM-L6-v2"
    
    # Agent config
    top_k: int = 3
    similarity_threshold: float = 0.55
    max_memory_cells: int = 1000
    experience_reward_decay: float = 0.9
    enable_emotions: bool = True
    