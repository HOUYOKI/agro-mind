"""
Ollama embedding wrapper for text retrieval.
"""

from typing import List

import requests
from chromadb.api.types import EmbeddingFunction
from langchain_core.embeddings import Embeddings

from backend.vision.config import config


class OllamaEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.model = config.embedding.model
        self.dimensions = config.embedding.dimensions
        self.query_prefix = config.embedding.query_prefix
        self.doc_prefix = config.embedding.doc_prefix
        self.ollama_url = "http://localhost:11434/api/embeddings"
        self.session = requests.Session()

    def _normalize(self, embedding: List[float]) -> List[float]:
        if not config.embedding.normalize:
            return embedding

        norm = sum(x * x for x in embedding) ** 0.5

        if norm == 0:
            return embedding

        return [x / norm for x in embedding]

    def _embed(self, text: str) -> List[float]:
        response = self.session.post(
            self.ollama_url,
            json={
                "model": self.model,
                "prompt": text,
            },
            timeout=60,
        )

        response.raise_for_status()

        embedding = response.json()["embedding"]

        if len(embedding) != self.dimensions:
            raise ValueError(
                f"Expected {self.dimensions} dimensions, "
                f"got {len(embedding)} from {self.model}"
            )

        return self._normalize(embedding)

    def __call__(self, input: List[str]) -> List[List[float]]:
        return [
            self._embed(self.doc_prefix + text)
            for text in input
        ]

    def embed_query(self, query: str) -> List[float]:
        return self._embed(self.query_prefix + query)


class OllamaEmbeddingsWrapper(Embeddings):
    def __init__(self):
        self.embedding_function = OllamaEmbeddingFunction()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embedding_function(texts)

    def embed_query(self, text: str) -> List[float]:
        return self.embedding_function.embed_query(text)


ollama_embeddings = OllamaEmbeddingFunction()
ollama_wrapper = OllamaEmbeddingsWrapper()


def get_embedding(text: str, for_query: bool = False) -> List[float]:
    if for_query:
        return ollama_embeddings.embed_query(text)

    return ollama_embeddings([text])[0]