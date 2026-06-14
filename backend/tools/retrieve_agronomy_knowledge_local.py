"""
Safe local RAG retrieval tool for Agro-Mind.

Uses:
- Ollama local embedding model: nomic-embed-text
- Local ChromaDB folder: backend/data/chromadb_local
- Collections:
  - collection_structured_local
  - collection_full_local

Returns [] safely if ChromaDB, Ollama, or retrieval fails.
"""

import os
from typing import Dict, Any, List, Optional

try:
    import ollama
except Exception:
    ollama = None

try:
    import chromadb
except Exception:
    chromadb = None


EMBED_MODEL = "nomic-embed-text"

CHROMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "chromadb_local"
)

_client = None
_col_struct = None
_col_full = None


QUERY_TYPE_FILTERS = {
    "disease": {"has_diseases": True},
    "pest": {"has_pests": True},
    "ingredient": {"has_ingredients": True},
    "safety": {"is_pesticide": True},
    "microbial": {"is_microbial": True},
    "fertilizer": {"is_fertilizer": True},
    "crop": None,
    "symptom": None,
    "dosage": None,
    "product_name": None,
    "chinese": None,
    "general": None,
}

FULL_DOC_TYPES = {"symptom", "chinese", "general", "safety"}


def _init() -> bool:
    """
    Initialize local ChromaDB collections safely.
    """
    global _client, _col_struct, _col_full

    if chromadb is None:
        return False

    if not os.path.exists(CHROMA_PATH):
        return False

    try:
        if _client is None:
            _client = chromadb.PersistentClient(path=CHROMA_PATH)
            _col_struct = _client.get_collection("collection_structured_local")
            _col_full = _client.get_collection("collection_full_local")

        return True

    except Exception:
        return False


def _embed_query(query: str) -> Optional[List[float]]:
    """
    Create query embedding using Ollama local model.
    """
    if ollama is None:
        return None

    try:
        embedding_response = ollama.embeddings(
            model=EMBED_MODEL,
            prompt=query[:2000]
        )

        if isinstance(embedding_response, dict):
            return embedding_response.get("embedding")

        return getattr(embedding_response, "embedding", None)

    except Exception:
        return None


def retrieve_agronomy_knowledge(
    query: str,
    query_type: str = "general",
    n_results: int = 3,
    use_full_docs: bool = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant agricultural product documents.

    Returns:
    List of dicts:
    - product_id
    - product_name
    - product_name_cn
    - detected_crop
    - detected_issue
    - document
    - distance
    - collection
    """

    if not query or not query.strip():
        return []

    if not _init():
        return []

    if use_full_docs is None:
        use_full_docs = query_type in FULL_DOC_TYPES

    collection = _col_full if use_full_docs else _col_struct
    where = QUERY_TYPE_FILTERS.get(query_type, None)

    q_vector = _embed_query(query)

    if not q_vector:
        return []

    kwargs = {
        "query_embeddings": [q_vector],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }

    if where:
        kwargs["where"] = where

    try:
        raw = collection.query(**kwargs)
    except Exception:
        return []

    results = []

    if raw and "ids" in raw and len(raw["ids"]) > 0:
        for i in range(len(raw["ids"][0])):
            metadata = raw["metadatas"][0][i] if raw.get("metadatas") else {}

            results.append({
                "product_id": raw["ids"][0][i],
                "product_name": metadata.get("product_name", "Agricultural Solution"),
                "product_name_cn": metadata.get("product_name_cn", "N/A"),
                "detected_crop": metadata.get("crop", metadata.get("target_crops", "Extracted from query")),
                "detected_issue": metadata.get(
                    "disease",
                    metadata.get("pest", metadata.get("target_diseases", "Extracted from query"))
                ),
                "document": raw["documents"][0][i] if raw.get("documents") else "",
                "distance": round(raw["distances"][0][i], 2) if raw.get("distances") else 0.0,
                "collection": "full" if use_full_docs else "structured",
            })

    return results


if __name__ == "__main__":
    print("=== LOCAL RAG TOOL TEST ===")
    tests = [
        ("citrus yellowing leaves", "symptom"),
        ("what treats root rot", "disease"),
        ("柑橘叶片发黄怎么处理", "chinese"),
        ("Bacillus subtilis", "ingredient"),
    ]

    for query, qtype in tests:
        print(f"\n[{qtype}] {query}")
        results = retrieve_agronomy_knowledge(query, query_type=qtype, n_results=2)
        for r in results:
            print(f'→ {r["product_id"]} | {r["product_name"]} | dist={r["distance"]}')