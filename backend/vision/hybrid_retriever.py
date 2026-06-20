"""
Hybrid retrieval for image diagnosis.

Flow:
1. Retrieve similar annotated images using CLIP image embeddings.
2. Extract likely crop/disease.
3. Retrieve matching products from product collection.
4. Retrieve similar historical support cases.
5. Rank products.
"""

from typing import Dict, Any, Optional

from backend.vision.config import config
from backend.vision.image_retriever import image_retriever
from backend.vision.retriever import retrieval_tool
from backend.vision.ranker import rank_products, pick_best_product


def build_diagnosis_query(
    crop: str,
    disease: str,
    disease_type: str = "",
    user_text: Optional[str] = None,
) -> str:
    parts = []

    if crop:
        parts.append(crop)

    if disease:
        parts.append(disease)

    if disease_type:
        parts.append(disease_type)

    if user_text:
        parts.append(user_text)

    if not parts:
        return "crop disease diagnosis treatment product"

    return " ".join(parts)


def hybrid_retrieve_for_image(
    image_path: str,
    user_text: Optional[str] = None,
    image_k: int = 5,
    product_k: int = 8,
    support_k: int = 3,
) -> Dict[str, Any]:
    image_result = image_retriever.diagnose(
        image_path=image_path,
        k=image_k,
    )

    if not image_result.get("success"):
        return {
            "success": False,
            "stage": "image_retrieval",
            "message": image_result.get("message", "Image retrieval failed."),
            "image_result": image_result,
        }

    crop = image_result.get("crop") or ""
    disease = image_result.get("disease") or ""
    disease_type = image_result.get("disease_type") or ""
    confidence = float(image_result.get("confidence") or 0.0)

    query = build_diagnosis_query(
        crop=crop,
        disease=disease,
        disease_type=disease_type,
        user_text=user_text,
    )

    products = retrieval_tool.search_products(
        query=query,
        k=product_k,
    )

    ranked_products = rank_products(
        products=products,
        crop=crop,
        disease=disease,
        disease_type=disease_type,
        top_k=product_k,
    )

    best_product = pick_best_product(ranked_products)

    support_query = disease or query

    support_cases = retrieval_tool.search_support_cases(
        query=support_query,
        k=support_k,
        category="diagnosis",
    )

    needs_human_review = confidence < config.retrieval.confidence_threshold

    return {
        "success": True,
        "query": query,
        "diagnosis": {
            "crop": crop,
            "disease": disease,
            "disease_type": disease_type,
            "confidence": round(confidence, 4),
            "needs_human_review": needs_human_review,
        },
        "best_product": best_product,
        "recommended_products": ranked_products,
        "historical_cases": support_cases,
        "similar_images": image_result.get("top_matches", []),
        "image_result": image_result,
    }