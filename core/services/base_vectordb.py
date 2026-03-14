from abc import ABC, abstractmethod
from typing import List, Dict


class BaseVectorDB(ABC):

    @abstractmethod
    def add(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict]
    ):
        pass


    @abstractmethod
    def query(
        self,
        query: str,
        top_k: int
    ):
        pass


    @abstractmethod
    def delete(
        self,
        ids: List[str]
    ):
        pass