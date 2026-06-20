"""
Product Recommender
Connected directly to AgroMind RAG V3.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
rag_v3_dir = os.path.join(backend_dir, "rag_v3")

if rag_v3_dir not in sys.path:
    sys.path.insert(0, rag_v3_dir)

from src.retrieval_tool import AgroMindRetriever

retriever = AgroMindRetriever()


def recommend_product(message: str) -> dict:
    try:
        results = retriever.search(message, k=3)

        if not results:
            return {
                "recommended_product": "Consult an agricultural expert",
                "reason": "No matching products found in AgroMind knowledge base.",
                "safety_note": "Please verify diagnosis before applying agricultural chemicals.",
                "detected_crop": "Unknown",
                "detected_issue": "Unknown"
            }

        doc, score = results[0]

        metadata = getattr(doc, "metadata", {}) or {}

        return {
            "recommended_product": (
                metadata.get("name_en")
                or metadata.get("name_cn")
                or "Unknown Product"
            ),
            "product_id": metadata.get("product_id"),
            "reason": doc.page_content[:500],
            "safety_note": (
                "Always follow official dosage instructions "
                "and safety precautions."
            ),
            "detected_crop": metadata.get("crops", []),
            "detected_issue": metadata.get("diseases", []),
            "score": float(score)
        }

    except Exception as e:
        return {
            "recommended_product": "CRITICAL: RAG Engine Error",
            "reason": str(e),
            "safety_note": "Check AgroMind RAG V3 configuration.",
            "detected_crop": "Error",
            "detected_issue": "Error"
        }