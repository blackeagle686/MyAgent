import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from llama_cpp import Llama
from sentence_transformers import SentenceTransformer
from huggingface_hub import hf_hub_download
from config import Config
import logging
import threading
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class LocalLLMService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LocalLLMService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.thinker_model = None
        self.thinker_tokenizer = None
        
        self.planner_model = None
        
        
        self.embedding_model = None
        
        self._initialized = True
        logger.info("LocalLLMService initialized (models not yet loaded)")

    def _load_thinker(self):
        """Loads Qwen/Qwen2.5-3B-Instruct with 8-bit quantization"""
        if self.thinker_model is not None:
            return

        logger.info(f"Loading thinker model: {Config.local_thinker_model}")
        
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False,
            )
            
            self.thinker_tokenizer = AutoTokenizer.from_pretrained(Config.local_thinker_model)
            self.thinker_model = AutoModelForCausalLM.from_pretrained(
                Config.local_thinker_model,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True
            )
            logger.info("Thinker model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load thinker model: {e}")
            raise

    def _load_planner(self):
        """Loads Qwen/Qwen2.5-Coder-3B-Instruct-GGUF using llama-cpp-python"""
        if self.planner_model is not None:
            return

        logger.info(f"Loading planner model: {Config.local_planner_model}")
        
        try:
            # We assume the user wants the q8_0 or similar high quality quantization
            # This logic might need refinement based on exact file names in the repo
            model_path = hf_hub_download(
                repo_id=Config.local_planner_model,
                filename="qwen2.5-coder-3b-instruct-q8_0.gguf" # Defaulting to q8_0 as per user request for quality
            )
            
            self.planner_model = Llama(
                model_path=model_path,
                n_ctx=32768,
                n_threads=4, # Adjust based on CPU
                verbose=False
            )
            logger.info("Planner model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load planner model: {e}")
            raise

    def _load_embedding(self):
        """Loads sentence-transformers/all-MiniLM-L6-v2"""
        if self.embedding_model is not None:
            return

        logger.info(f"Loading embedding model: {Config.local_embedding_model}")
        
        try:
            self.embedding_model = SentenceTransformer(Config.local_embedding_model, device='cpu')
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def generate_thinker(self, prompt: str, system_prompt: str = "You are a helpful assistant.", max_tokens: int = 512) -> str:
        self._load_thinker()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        text = self.thinker_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = self.thinker_tokenizer([text], return_tensors="pt").to(self.thinker_model.device)

        generated_ids = self.thinker_model.generate(
            model_inputs.input_ids,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7
        )
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        return self.thinker_tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    def generate_planner(self, prompt: str, system_prompt: str = "You are a coding expert.", max_tokens: int = 1024) -> str:
        self._load_planner()
        
        output = self.planner_model.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.2
        )
        return output["choices"][0]["message"]["content"]

    def embed(self, text: str) -> List[float]:
        self._load_embedding()
        
        embeddings = self.embedding_model.encode(text).tolist()
            
        return embeddings

# Singleton instance access
local_llm_service = LocalLLMService()
