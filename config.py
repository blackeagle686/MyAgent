from dataclasses import dataclass

@dataclass
class Config:
    # OpenRouter API config
    api_key: str = "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"
    base_url: str = "https://openrouter.ai/api/v1"
    
    # LLMs  
    embedding_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    search_model: str = "nousresearch/hermes-3-llama-3.1-405b:free"
    # model: str = "qwen/qwen3-vl-30b-a3b-thinking"
    # model: str = "z-ai/glm-4.5-air:free"
    model : str = "nvidia/nemotron-3-super-120b-a12b:free"
    vdb_model: str = "all-MiniLM-L6-v2"
    
    # Agent config
    top_k: int = 3
    similarity_threshold: float = 0.55
    max_memory_cells: int = 1000
    experience_reward_decay: float = 0.9
    enable_emotions: bool = True
    