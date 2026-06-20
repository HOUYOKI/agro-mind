"""
RAG adapter for Agro-Mind backend.

This connects the main FastAPI backend to Ohoud's RAG V3 system.
The backend keeps calling retrieve_agronomy_knowledge(), but behind the scenes
we now use the LangChain + ChromaDB V3 retriever.
"""

from pathlib import Path
import sys
from typing import Dict, Any, List


# Path to backend/rag_v3
RAG_V3_ROOT = Path(__file__).resolve().parents[1] / "rag_v3"

# Allow imports like: from src.retrieval_tool import AgroMindRetriever
if str(RAG_V3_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_V3_ROOT))


_retriever = None


def get_retriever():
    """
    Lazy-load the V3 retriever once.
    This avoids loading ChromaDB on every /chat request.
    """
    global _retriever

    if _retriever is None:
        from src.retrieval_tool import AgroMindRetriever
        _retriever = AgroMindRetriever()

    return _retriever


def _doc_to_source(doc, score) -> Dict[str, Any]:
    """
    Convert LangChain Document output into the stable format expected by main.py.
    """
    metadata = getattr(doc, "metadata", {}) or {}

    return {
        "product_id": metadata.get("product_id"),
        "product_name": metadata.get("name_en") or metadata.get("name_cn"),
        "product_name_cn": metadata.get("name_cn"),
        "diseases": metadata.get("diseases", []),
        "crops": metadata.get("crops", []),
        "pests": metadata.get("pests", []),
        "ingredients": metadata.get("ingredients", []),
        "symptoms": metadata.get("symptoms", []),
        "score": float(score) if isinstance(score, (int, float)) else score,
        "document": getattr(doc, "page_content", "")
    }


def retrieve_agronomy_knowledge(
    query: str,
    query_type: str = "general",
    n_results: int = 3
) -> Dict[str, Any]:
    """
    Main RAG function used by backend/main.py.

    Returns:
    {
      "rag_used": bool,
      "found": bool,
      "summary": str,
      "sources": list,
      "confidence": float,
      "status": str
    }
    """
    try:
        retriever = get_retriever()

        if query_type == "disease":
            results = retriever.search_by_disease(query, k=n_results)
        elif query_type == "crop":
            results = retriever.search_by_crop(query, k=n_results)
        elif query_type == "ingredient":
            results = retriever.search_by_ingredient(query, k=n_results)
        else:
            results = retriever.search(query, k=n_results)

        sources: List[Dict[str, Any]] = [
            _doc_to_source(doc, score) for doc, score in results
        ]

        if not sources:
            return {
                "rag_used": True,
                "found": False,
                "summary": "No relevant product knowledge found.",
                "sources": [],
                "confidence": 0.0,
                "status": "no_results"
            }

        top = sources[0]
        product_name = top.get("product_name") or top.get("product_name_cn") or "Unknown product"
        product_id = top.get("product_id") or "Unknown ID"

        summary = (
            f"Top match: {product_name} "
            f"(ID: {product_id}). "
            f"Relevant knowledge was retrieved from the Agro-Mind V3 product database."
        )

        return {
            "rag_used": True,
            "found": True,
            "summary": summary,
            "sources": sources,
            "confidence": 0.85,
            "status": "success"
        }

    except Exception as error:
        return {
            "rag_used": False,
            "found": False,
            "summary": "RAG retrieval failed. Using fallback response.",
            "sources": [],
            "confidence": 0.0,
            "status": "error",
            "error": str(error)
        }