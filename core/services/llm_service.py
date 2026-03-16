from openai import OpenAI
from config import Config
import logging
import json
import os
import hashlib
import time
from typing import Optional, Any, Dict
from sentence_transformers import SentenceTransformer
from core.services.local_llm_service import local_llm_service

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
        
        # Rate limit and Cache state
        self.rate_limits: Dict[str, Any] = {}
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "cache")
        if Config.enable_cache and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_cache_key(self, prompt: str, model: str, system_prompt: Optional[str], temperature: float) -> str:
        data = f"{prompt}:{model}:{system_prompt}:{temperature}"
        return hashlib.md5(data.encode()).hexdigest()

    def _check_cache(self, key: str) -> Optional[str]:
        if not Config.enable_cache:
            return None
        cache_path = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f).get("content")
            except Exception as e:
                logger.error(f"Cache read error: {e}")
        return None

    def _update_cache(self, key: str, content: str):
        if not Config.enable_cache:
            return
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
            cache_key = self._get_cache_key(user_prompt, target_model, sys_prompt, temperature)
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
            logger.error(f"OpenRouter Error: {e}. Falling back to local LLM.")
            try:
                # Fallback to local
                if target_model == self.coder_model:
                     return local_llm_service.generate_planner(user_prompt, sys_prompt, max_tokens)
                else:
                     return local_llm_service.generate_thinker(user_prompt, sys_prompt, max_tokens)
            except Exception as local_e:
                logger.error(f"Local LLM Error: {local_e}")
                return "LLM generation failed (both OpenRouter and Local)"
    
    def embed(self, text): 
        try:
            embedding = self.client.embeddings.create(
                extra_headers={},
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            return embedding.data[0].embedding
        except Exception as e:
            logger.warning(f"OpenRouter Embedding failed for {self.embedding_model}, falling back to local embedding: {e}")
            try:
                return local_llm_service.embed(text)
            except Exception as local_e:
                logger.error(f"Local Embedding Error: {local_e}")
                # Return a generic 384-dim zero vector (standard for Small MiniLM)
                return [0.0] * 384

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