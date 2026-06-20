"""
Product Recommender
Connected directly to AgroMind RAG V3.
"""

import os
import sys
import time
from typing import Any, Dict


current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
rag_v3_dir = os.path.join(backend_dir, "rag_v3")

if rag_v3_dir not in sys.path:
    sys.path.insert(0, rag_v3_dir)

from src.retrieval_tool import AgroMindRetriever


_retriever = None


def get_retriever() -> AgroMindRetriever:
    """
    Lazy-load retriever once to avoid reloading ChromaDB on every request.
    """
    global _retriever

    if _retriever is None:
        _retriever = AgroMindRetriever()

    return _retriever


def _safe_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _score_to_confidence(score: Any) -> float:
    """
    Converts similarity/distance-ish scores into a safe display confidence.
    This is heuristic because retriever score meaning depends on backend.
    """
    try:
        score = float(score)

        if score < 0:
            return 0.0

        # If score looks like a distance, smaller is better.
        if score <= 1:
            confidence = 1 / (1 + score)
        else:
            confidence = 1 / (1 + abs(score))

        return round(max(0.0, min(1.0, confidence)), 2)

    except Exception:
        return 0.5


def recommend_product(message: str) -> Dict[str, Any]:
    start = time.time()

    try:
        retriever = get_retriever()
        results = retriever.search(message, k=3)

        print(
            f"\nPRODUCT RETRIEVER TIME: "
            f"{round(time.time() - start, 2)} sec"
        )

        if not results:
            return {
                "recommended_product": None,
                "product_id": None,
                "reason": "No matching products found in AgroMind knowledge base.",
                "safety_note": "Please verify the crop issue with an agricultural expert before applying any chemical product.",
                "detected_crop": [],
                "detected_issue": [],
                "score": None,
                "confidence": 0.0,
                "status": "no_results",
            }

        doc, score = results[0]
        metadata = getattr(doc, "metadata", {}) or {}

        product_name = (
            metadata.get("name_en")
            or metadata.get("name_cn")
            or "Unknown Product"
        )

        return {
            "recommended_product": product_name,
            "product_id": metadata.get("product_id"),
            "reason": getattr(doc, "page_content", "")[:500],
            "safety_note": (
                "Always follow the official product label and local agricultural guidance. "
                "Do not use exact dosage, dilution, or harvest timing unless confirmed by the label or an expert."
            ),
            "detected_crop": _safe_list(metadata.get("crops", [])),
            "detected_issue": _safe_list(metadata.get("diseases", [])),
            "pests": _safe_list(metadata.get("pests", [])),
            "ingredients": _safe_list(metadata.get("ingredients", [])),
            "symptoms": _safe_list(metadata.get("symptoms", [])),
            "score": float(score) if isinstance(score, (int, float)) else score,
            "confidence": _score_to_confidence(score),
            "status": "success",
        }

    except Exception as error:
        print("PRODUCT RECOMMENDER ERROR:", error)

        return {
            "recommended_product": None,
            "product_id": None,
            "reason": "Product retrieval failed. Please check the AgroMind RAG V3 configuration.",
            "safety_note": "No product recommendation should be made until retrieval is working.",
            "detected_crop": [],
            "detected_issue": [],
            "score": None,
            "confidence": 0.0,
            "status": "error",
            "error": str(error),
        }