from openai import OpenAI
from config import Config
import logging
from typing import Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=Config.base_url,
            api_key=Config.api_key
            )
        
        self.model = Config.model
        self.embedding_model = Config.embedding_model
        self.search_model = Config.search_model
        
    def generate(self, user_prompt: str, memory=None,
                sys_prompt: Optional[str] = None,
                temperature: float = 0.3,
                max_tokens: int = 2000) -> str:

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

            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=messages
            )

            response = completion.choices[0].message.content

            # store response in memory
            memory.append({"role":"user","content":user_prompt})
            memory.append({"role":"assistant","content":response})

            return response

        except Exception as e:
            logger.error(f"LLM Error : {e}")
            return "LLM generation failed"
    
    def embed(self, text): 
        embedding = self.client.embeddings.create(
            extra_headers={},
            model=self.embedding_model,
            input=text,
            encoding_format="float"
        )
        return embedding.data[0].embedding

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