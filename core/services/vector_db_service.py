import chromadb
import logging
from typing import List,Dict,Optional
from chromadb.utils import embedding_functions
from base_vectordb import BaseVectorDB
from config import Config


logger = logging.getLogger(__name__)

class ChromaVectorDB(BaseVectorDB):
    def __init__(
        self,
        collection_name:str,
        persist_dir:str="./chroma",
        model:str= Config.vdb_model
    ):
        try:
            self.client = chromadb.Client(
                chromadb.config.Settings(
                    persist_directory=persist_dir,
                    anonymized_telemetry=False
                )
            )
            self.embedding = embedding_functions\
                .SentenceTransformerEmbeddingFunction(
                    model_name=model
                )
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding
            )
            logger.info("VectorDB initialized")
        except Exception as e:
            logger.error(e)
            raise

    def add(self,
            ids:List[str],
            documents:List[str],
            metadatas:Optional[List[Dict]]=None ):
        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

        except Exception as e:
            logger.error(e)

    def query(
        self,
        query:str,
        top_k:int= Config.top_k
    ):
        try:
            return self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
        except Exception as e:
            logger.error(e)
            return []


    def delete(self, ids):
        try:
            self.collection.delete(ids=ids)

        except Exception as e:
            logger.error(e)