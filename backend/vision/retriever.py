"""
Unified AgroMind Retriever.

Collections:
- Structured Product Collection
- Historical Support Collection
"""

from typing import Dict, List, Optional, Any

import chromadb

from backend.vision.config import config
from backend.vision.embeddings import ollama_wrapper


class AgroMindRetriever:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=config.chromadb_path
        )

        self.products = self.client.get_collection(
            config.retrieval.structured_collection
        )

        self.support = self.client.get_collection(
            config.retrieval.full_collection
        )

        self.embeddings = ollama_wrapper

        self._validate_collections()

    def _validate_collections(self):
        if self.products.count() == 0:
            raise RuntimeError(
                f"{config.retrieval.structured_collection} is empty"
            )

        if self.support.count() == 0:
            raise RuntimeError(
                f"{config.retrieval.full_collection} is empty"
            )

    def _embed_query(self, query: str):
        return self.embeddings.embed_query(query)

    def _normalize_distance(self, distance: float) -> float:
        return round(float(distance), 4)

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        result = self.products.get(ids=[product_id])

        if not result.get("ids"):
            return None

        metadata = result["metadatas"][0]

        return {
            "product_id": metadata.get("product_id"),
            "name_cn": metadata.get("name_cn"),
            "name_en": metadata.get("name_en"),
            "product_type": metadata.get("product_type"),
            "diseases": metadata.get("diseases", []),
            "crops": metadata.get("crops", []),
            "is_pesticide": metadata.get("is_pesticide", False),
            "is_microbial": metadata.get("is_microbial", False),
            "is_fertilizer": metadata.get("is_fertilizer", False),
        }

    def search_products(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self._embed_query(query)

        results = self.products.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=[
                "metadatas",
                "distances",
            ],
        )

        products = []

        if not results.get("metadatas") or not results["metadatas"][0]:
            return products

        for metadata, distance in zip(
            results["metadatas"][0],
            results["distances"][0],
        ):
            products.append(
                {
                    "product_id": metadata.get("product_id"),
                    "name_cn": metadata.get("name_cn"),
                    "name_en": metadata.get("name_en"),
                    "product_type": metadata.get("product_type"),
                    "diseases": metadata.get("diseases", []),
                    "crops": metadata.get("crops", []),
                    "is_pesticide": metadata.get("is_pesticide", False),
                    "is_microbial": metadata.get("is_microbial", False),
                    "is_fertilizer": metadata.get("is_fertilizer", False),
                    "distance": self._normalize_distance(distance),
                }
            )

        return products

    def search_support_cases(
        self,
        query: str,
        k: int = 3,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query_embedding = self._embed_query(query)

        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": k,
            "include": [
                "documents",
                "metadatas",
                "distances",
            ],
        }

        if category:
            query_kwargs["where"] = {
                "category": category,
            }

        try:
            results = self.support.query(**query_kwargs)

        except Exception:
            query_kwargs.pop("where", None)
            results = self.support.query(**query_kwargs)

        cases = []

        if not results.get("documents") or not results["documents"][0]:
            return cases

        for document, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            cases.append(
                {
                    "category": metadata.get("category"),
                    "source": metadata.get("source"),
                    "conversation": document,
                    "distance": self._normalize_distance(distance),
                }
            )

        return cases

    def search_disease_products(self, disease: str, k: int = 5) -> List[Dict[str, Any]]:
        return self.search_products(
            query=disease,
            k=k,
        )

    def retrieve_context(
        self,
        query: str,
        product_k: int = 5,
        support_k: int = 3,
        support_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "products": self.search_products(
                query=query,
                k=product_k,
            ),
            "support_cases": self.search_support_cases(
                query=query,
                k=support_k,
                category=support_category,
            ),
        }

    def health(self) -> Dict[str, Any]:
        return {
            "structured_collection": self.products.count(),
            "support_collection": self.support.count(),
            "embedding_model": config.embedding.model,
        }


retrieval_tool = AgroMindRetriever()