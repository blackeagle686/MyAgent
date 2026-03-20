from openai import OpenAI
from config import Config
import logging
import json
import os
import hashlib
import time
from typing import Optional, Any, Dict, List
from sentence_transformers import SentenceTransformer
from core.services.local_llm_service import local_llm_service

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
    # Path found for all-MiniLM-L6-v2
    _tokenizer_path = "/home/tlk/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf/tokenizer.json"
    if os.path.exists(_tokenizer_path):
        _rust_tokenizer = RustTokenizer(_tokenizer_path)
    else:
        _rust_tokenizer = None
except ImportError:
    _rust_engine = None
    _rust_cache = None
    _rust_orchestrator = None
    _rust_tokenizer = None

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=Config.base_url,
            api_key=Config.api_key
            )
        
        self.model = Config.model
        self.coder_model = Config.coder_model
        self.embedding_model = Config.embedding_model
        self.search_model = Config.search_model
        
        # State
        self.rate_limits: Dict[str, Any] = {}
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "cache")
        if Config.enable_cache and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_cache_key(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    def _check_cache(self, key: str) -> Optional[str]:
        if not Config.enable_cache: return None
        cache_path = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f).get("content")
            except Exception as e:
                logger.error(f"Cache read error: {e}")
        return None

    def _update_cache(self, key: str, content: str):
        if not Config.enable_cache: return
        cache_path = os.path.join(self.cache_dir, f"{key}.json")
        try:
            with open(cache_path, 'w') as f:
                json.dump({"content": content, "timestamp": time.time()}, f)
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    def _update_rate_limits(self, response_headers: Any):
        # OpenRouter headers: x-ratelimit-limit-requests, x-ratelimit-remaining-requests, etc.
        for key, value in response_headers.items():
            if key.startswith("x-ratelimit-"):
                self.rate_limits[key] = value
        
        # Proactive logging if limits are low
        remaining = self.rate_limits.get("x-ratelimit-remaining-requests")
        if remaining and int(remaining) < 5:
            logger.warning(f"Rate limit low: {remaining} requests remaining.")
        
    def generate(self, user_prompt: str, memory=None,
                sys_prompt: Optional[str] = None,
                temperature: float = 0.3,
                max_tokens: int = 4096,
                model: Optional[str] = None) -> str:

        if not sys_prompt:
            sys_prompt = "You are an intelligent AI assistant"

        messages = [
            {
                "role": "system",
                "content": sys_prompt
            }
        ]

        if not isinstance(memory, list):
            if memory is not None:
                logger.warning("Memory passed as non-list (%s), ignoring. Use named arguments for sys_prompt.", type(memory))
            memory = []

        # add memory
        messages.extend(memory)

        # add current user message
        messages.append(
            {
                "role": "user",
                "content": user_prompt
            }
        )
        try:
            target_model = model or self.model
            
            # 1. Caching
            cache_key = self._get_cache_key(f"{user_prompt}:{target_model}:{sys_prompt}:{temperature}")
            cached_response = self._check_cache(cache_key)
            if cached_response:
                logger.info("Using cached LLM response")
                return cached_response

            # 2. API Call with Retry Logic
            retries = 0
            while retries <= Config.max_retries:
                try:
                    completion = self.client.chat.completions.create(
                        model=target_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        messages=messages
                    )
                    
                    # Capture headers if available (OpenAI client might require raw response)
                    # For simplicity, we assume standard behavior or fallback to standard logging
                    
                    response = completion.choices[0].message.content
                    
                    # Store response in cache
                    self._update_cache(cache_key, response)

                    # Store response in memory
                    memory.append({"role":"user","content":user_prompt})
                    memory.append({"role":"assistant","content":response})

                    return response

                except Exception as e:
                    if "429" in str(e) or "rate_limit" in str(e).lower():
                        retries += 1
                        if retries <= Config.max_retries:
                            wait_time = Config.backoff_factor ** retries
                            logger.warning(f"Rate limit hit. Retrying in {wait_time}s... (Attempt {retries}/{Config.max_retries})")
                            time.sleep(wait_time)
                            continue
                    raise e # Re-raise if not a rate limit or max retries reached

        except Exception as e:
            logger.error(f"LLM Error: {e}. Falling back to local.")
            try:
                # Fallback to local
                if target_model == self.coder_model:
                     return local_llm_service.generate_planner(user_prompt, sys_prompt, max_tokens)
                else:
                     return local_llm_service.generate_thinker(user_prompt, sys_prompt, max_tokens)
            except Exception as local_e:
                logger.error(f"Local LLM Error: {local_e}")
                return "LLM generation failed (both OpenRouter and Local)"
    
    def embed(self, text: str) -> List[float]:
        if Config.use_rust_accelerator and _rust_cache:
            cache_key = self._get_cache_key(text)
            cached_vec = _rust_cache.get(cache_key)
            if cached_vec:
                return cached_vec

        try:
            embedding = self.client.embeddings.create(
                extra_headers={},
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            vec = embedding.data[0].embedding
            
            if Config.use_rust_accelerator and _rust_cache:
                _rust_cache.set(cache_key, vec)
            
            return vec
        except Exception as e:
            logger.warning(f"Embedding failed, falling back to local: {e}")
            vec = local_llm_service.embed(text)
            if Config.use_rust_accelerator and _rust_cache:
                _rust_cache.set(self._get_cache_key(text), vec)
            return vec

    def generate_parallel(self, prompts: List[str], sys_prompt: str = None) -> List[str]:
        """Fire off multiple requests in parallel using Rust orchestrator."""
        if Config.use_rust_accelerator and _rust_orchestrator:
            urls = [f"{Config.base_url}/chat/completions"] * len(prompts)
            payloads = []
            for p in prompts:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": sys_prompt or "You are an assistant"},
                        {"role": "user", "content": p}
                    ]
                }
                payloads.append(json.dumps(payload))
            
            # Note: This simple implementation might need to handle headers/API keys
            # In a real system, we'd pass the API key to the Rust layer.
            # For now, let's assume the Rust orchestrator can be extended or handles it.
            return _rust_orchestrator.request_batch(urls, payloads)
        
        # Fallback to serial
        return [self.generate(p, sys_prompt=sys_prompt) for p in prompts]

    def count_tokens(self, text: str) -> int:
        if Config.use_rust_accelerator and _rust_tokenizer:
            return _rust_tokenizer.count_tokens(text)
        # Simple whitespace fallback if tokenizer is missing
        return len(text.split())

    def deep_search(self, query): 
        completion = self.client.chat.completions.create(
            extra_headers={},
            extra_body={},
            model= self.search_model,
            messages=[
                {
                "role": "user",
                "content": f"{query}"
                }
            ]
        )
        return completion.choices[0].message.content

class Encoder(LLMClient):
    def encode(self, text):
        return self.embed(text)

class Searcher(LLMClient):
    def search(self, query):
        return self.deep_search(query)
        
# load pretrained embedding model
client = LLMClient()
encoder_client = Encoder()
search_client = Searcher()