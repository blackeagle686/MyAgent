import logging
import uuid
import json
from typing import Optional, Dict, Any
from core.services.vector_db_service import ChromaVectorDB
from config import Config

logger = logging.getLogger(__name__)

class SemanticCacheService:
    """
    Semantic Cache service using ChromaDB to store and retrieve LLM completions
    based on the semantic similarity of the prompts.
    """

    def __init__(self):
        self.vdb = ChromaVectorDB(
            collection_name="llm_semantic_cache",
            persist_dir="./chroma",
            model=Config.vdb_model
        )
        self.threshold = Config.semantic_cache_threshold

    def get(self, prompt: str, model: str) -> Optional[str]:
        """
        Retrieve a cached response if a semantically similar prompt exists.
        Searches the prompt (document) and returns the cached response from metadata.
        """
        if not Config.enable_cache:
            return None

        try:
            results = self.vdb.collection.query(
                query_texts=[prompt],
                n_results=1,
                where={"model": model}
            )

            if results and results['documents'] and results['distances'] and results['distances'][0]:
                distance = results['distances'][0][0]
                if distance < (1 - self.threshold):
                    logger.info(f"Semantic cache hit (dist: {distance:.4f})")
                    return results['metadatas'][0][0].get("response")
            
            return None
        except Exception as e:
            logger.error(f"Semantic cache retrieval error: {e}")
            return None

    def set(self, prompt: str, response: str, model: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Store a response in the semantic cache.
        The prompt is stored as the document (to be embedded) and the response in metadata.
        """
        if not Config.enable_cache:
            return

        try:
            cache_id = str(uuid.uuid4())
            meta = metadata or {}
            meta["model"] = model
            meta["response"] = response
            
            self.vdb.collection.add(
                ids=[cache_id],
                documents=[prompt],
                metadatas=[meta]
            )
            logger.debug(f"Saved to semantic cache: {cache_id}")
        except Exception as e:
            logger.error(f"Semantic cache storage error: {e}")

# Singleton instance
semantic_cache = SemanticCacheService()