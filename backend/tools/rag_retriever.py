from typing import Dict, Any, List

from backend.tools.retrieve_agronomy_knowledge_local import (
    retrieve_agronomy_knowledge as retrieve_local_knowledge
)


def retrieve_agronomy_knowledge(
    query: str,
    intent: str = "general",
    n_results: int = 3
) -> Dict[str, Any]:
    """
    Adapter between local RAG and main.py.

    Local RAG returns a list of product documents.
    main.py expects a structured dictionary.
    """

    try:
        results: List[Dict[str, Any]] = retrieve_local_knowledge(
            query=query,
            query_type=_intent_to_query_type(intent),
            n_results=n_results
        )

        if not results:
            return {
                "rag_used": True,
                "found": False,
                "summary": "No relevant agronomy knowledge was found.",
                "sources": [],
                "confidence": 0.0,
                "status": "no_results"
            }

        best_result = results[0]

        sources = [
            {
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "product_name_cn": item.get("product_name_cn"),
                "distance": item.get("distance"),
                "collection": item.get("collection"),
            }
            for item in results
        ]

        summary = _shorten_document(best_result.get("document", ""))

        return {
            "rag_used": True,
            "found": True,
            "summary": summary,
            "sources": sources,
            "confidence": 0.75,
            "status": "completed"
        }

    except Exception as error:
        return {
            "rag_used": True,
            "found": False,
            "summary": "RAG retrieval failed safely.",
            "sources": [],
            "confidence": 0.0,
            "status": f"failed: {str(error)}"
        }


def _intent_to_query_type(intent: str) -> str:
    mapping = {
        "crop_diagnosis": "symptom",
        "product_question": "general",
        "pesticide_safety": "safety",
        "general_question": "general",
        "disease": "disease",
        "pest": "pest",
        "symptom": "symptom",
        "safety": "safety",
    }

    return mapping.get(intent, "general")


def _shorten_document(document: str, max_chars: int = 900) -> str:
    """
    Keep RAG summary useful but not massive.
    """
    if not document:
        return "Relevant agronomy knowledge was found."

    document = document.strip()

    if len(document) <= max_chars:
        return document

    return document[:max_chars].rstrip() + "..."