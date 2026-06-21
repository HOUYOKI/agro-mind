"""
Product Recommender
Connected directly to AgroMind RAG V3.

This version keeps RAG/product retrieval working, but prevents raw Chinese
metadata from being displayed as detected crop / issue in the frontend.
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional


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


def _safe_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()

    if not text:
        return []

    # Handle comma-separated metadata safely.
    if "," in text:
        return [item.strip() for item in text.split(",") if item.strip()]

    return [text]


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


def _first_clean(value: Any, fallback: Optional[str] = None) -> Optional[str]:
    """
    Return one clean display value from a list/string/unknown value.
    """
    items = _safe_list(value)

    if not items:
        return fallback

    return items[0]


def _infer_crop_from_message(message: str) -> Optional[str]:
    """
    Extract a simple user-facing crop name from the user's message.
    This prevents the UI from showing the full RAG metadata crop list.
    """
    text = message.lower()

    crop_keywords = {
        "pumpkin": "Pumpkin",
        "pumpkins": "Pumpkin",
        "tomato": "Tomato",
        "tomatoes": "Tomato",
        "cucumber": "Cucumber",
        "cucumbers": "Cucumber",
        "pepper": "Pepper",
        "peppers": "Pepper",
        "chili": "Pepper",
        "chilli": "Pepper",
        "citrus": "Citrus",
        "orange": "Citrus",
        "oranges": "Citrus",
        "lemon": "Citrus",
        "lemons": "Citrus",
        "apple": "Apple",
        "apples": "Apple",
        "grape": "Grape",
        "grapes": "Grape",
        "rice": "Rice",
        "wheat": "Wheat",
        "corn": "Corn",
        "maize": "Corn",
        "rose": "Rose",
        "roses": "Rose",
        "lettuce": "Lettuce",
        "potato": "Potato",
        "potatoes": "Potato",
        "onion": "Onion",
        "onions": "Onion",
        "strawberry": "Strawberry",
        "strawberries": "Strawberry",
    }

    for keyword, crop in crop_keywords.items():
        if keyword in text:
            return crop

    return None


def _infer_issue_from_message(message: str) -> Optional[str]:
    """
    Extract a simple user-facing issue from the user's message.
    This prevents the UI from showing the full RAG metadata disease list.
    """
    text = message.lower()

    issue_keywords = {
        "rotting": "Rotting / possible crop disease",
        "rot": "Rotting / possible crop disease",
        "root rot": "Root rot",
        "yellow": "Yellowing leaves",
        "yellowing": "Yellowing leaves",
        "spots": "Leaf spots",
        "spot": "Leaf spots",
        "mold": "Mold / fungal symptoms",
        "mould": "Mold / fungal symptoms",
        "fungus": "Fungal disease symptoms",
        "fungal": "Fungal disease symptoms",
        "wilting": "Wilting",
        "wilt": "Wilting",
        "aphid": "Aphids",
        "aphids": "Aphids",
        "pest": "Pest damage",
        "pests": "Pest damage",
        "insect": "Insect damage",
        "insects": "Insect damage",
        "mildew": "Mildew",
        "blight": "Blight",
        "rust": "Rust disease",
        "dry": "Drying symptoms",
        "drying": "Drying symptoms",
        "dying": "Plant decline",
    }

    # Check longer/more specific phrases first.
    for keyword in sorted(issue_keywords.keys(), key=len, reverse=True):
        if keyword in text:
            return issue_keywords[keyword]

    return None


def _clean_product_reason(product_name: str, product_id: Optional[str], message: str) -> str:
    """
    Short frontend-safe product reason.
    Do not expose raw product metadata or Chinese RAG document text here.
    """
    crop = _infer_crop_from_message(message)
    issue = _infer_issue_from_message(message)

    if crop and issue:
        return (
            f"Matched {product_name} as a relevant product candidate for "
            f"{crop} with {issue.lower()} based on the Agro-Mind product knowledge base."
        )

    if crop:
        return (
            f"Matched {product_name} as a relevant product candidate for "
            f"{crop} based on the Agro-Mind product knowledge base."
        )

    if issue:
        return (
            f"Matched {product_name} as a relevant product candidate for "
            f"{issue.lower()} based on the Agro-Mind product knowledge base."
        )

    return (
        f"Matched {product_name} as a relevant product candidate from "
        f"the Agro-Mind product knowledge base."
    )


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
                "detected_crop": _infer_crop_from_message(message),
                "detected_issue": _infer_issue_from_message(message),
                "score": None,
                "confidence": 0.0,
                "status": "no_results",
            }

        doc, score = results[0]
        metadata = getattr(doc, "metadata", {}) or {}
        raw_page_content = getattr(doc, "page_content", "") or ""

        product_name = (
            metadata.get("name_en")
            or metadata.get("product_name_en")
            or metadata.get("name")
            or metadata.get("name_cn")
            or metadata.get("product_name")
            or "Unknown Product"
        )

        product_id = metadata.get("product_id")

        detected_crop = _infer_crop_from_message(message)
        detected_issue = _infer_issue_from_message(message)

        # Fallbacks should be short. Never use full metadata lists as UI labels.
        if not detected_crop:
            detected_crop = _first_clean(metadata.get("primary_crop")) or "Crop issue"

        if not detected_issue:
            detected_issue = _first_clean(metadata.get("primary_disease")) or "Possible crop disease"

        clean_reason = _clean_product_reason(product_name, product_id, message)

        return {
            "recommended_product": product_name,
            "product_id": product_id,

            # Frontend-safe fields.
            "reason": clean_reason,
            "detected_crop": detected_crop,
            "detected_issue": detected_issue,

            "safety_note": (
                "Always follow the official product label and local agricultural guidance. "
                "Do not use exact dosage, dilution, or harvest timing unless confirmed by the label or an expert."
            ),

            # Keep detailed RAG metadata separate for debugging / optional backend use.
            # Frontend should not display these as detected crop/issue.
            "rag_context": raw_page_content[:1200],
            "matched_metadata": {
                "crops": _safe_list(metadata.get("crops", []))[:10],
                "diseases": _safe_list(metadata.get("diseases", []))[:10],
                "pests": _safe_list(metadata.get("pests", []))[:10],
                "ingredients": _safe_list(metadata.get("ingredients", []))[:10],
                "symptoms": _safe_list(metadata.get("symptoms", []))[:10],
            },

            # Backward-compatible detailed fields, but limited.
            "pests": _safe_list(metadata.get("pests", []))[:5],
            "ingredients": _safe_list(metadata.get("ingredients", []))[:5],
            "symptoms": _safe_list(metadata.get("symptoms", []))[:5],

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
            "detected_crop": _infer_crop_from_message(message),
            "detected_issue": _infer_issue_from_message(message),
            "score": None,
            "confidence": 0.0,
            "status": "error",
            "error": str(error),
        }