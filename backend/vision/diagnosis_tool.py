"""
Vision diagnosis tool for Agro-Mind.

This is the backend-safe entrypoint:

image path
→ image retrieval diagnosis
→ hybrid product/support retrieval
→ ranked products
→ safe response payload
"""

from typing import Dict, Any, Optional

from backend.vision.config import config
from backend.vision.hybrid_retriever import hybrid_retrieve_for_image


# ==========================================
# SIMPLE DISPLAY TRANSLATIONS
# ==========================================

TRANSLATIONS = {
    "玫瑰": "rose",
    "黑斑病": "black spot disease",
    "苹果": "apple",
    "苹果树": "apple tree",
    "轮纹病": "ring rot disease",
    "番茄": "tomato",
    "早疫病": "early blight",
    "柑橘": "citrus",
    "疮痂病": "scab disease",
    "炭疽病": "anthracnose",
    "白粉病": "powdery mildew",
    "霜霉病": "downy mildew",
    "灰霉病": "gray mold",
    "根腐病": "root rot",
    "叶斑病": "leaf spot",
    "软腐病": "soft rot",
    "溃疡病": "canker disease",
    "真菌病害": "fungal disease",
    "细菌病害": "bacterial disease",
    "虫害": "pest damage",
}


def translate_label(value: Optional[str]) -> str:
    if not value:
        return ""

    return TRANSLATIONS.get(value, value)


# ==========================================
# HELPERS
# ==========================================

def _product_display_name(product: Optional[Dict[str, Any]]) -> Optional[str]:
    if not product:
        return None

    return (
        product.get("name_en")
        or product.get("product_name")
        or product.get("name_cn")
        or product.get("product_id")
    )


def _get_product_score(product: Optional[Dict[str, Any]]) -> float:
    if not product:
        return 0.0

    try:
        return float(product.get("rank_score", 0.0))
    except Exception:
        return 0.0


def _is_weak_product_match(product: Optional[Dict[str, Any]]) -> bool:
    product_score = _get_product_score(product)
    return product_score < 0.35


def _build_safe_vision_response(result: Dict[str, Any]) -> str:
    diagnosis = result.get("diagnosis", {})
    best_product = result.get("best_product")

    crop = translate_label(diagnosis.get("crop")) or "the crop"
    disease = translate_label(diagnosis.get("disease")) or "a possible issue"

    needs_human_review = diagnosis.get("needs_human_review", True)

    product_name = _product_display_name(best_product)
    weak_product_match = _is_weak_product_match(best_product)

    if needs_human_review:
        if product_name and not weak_product_match:
            return (
                f"The image looks similar to cases involving {crop} and {disease}, "
                f"but the confidence is not high enough for an automatic diagnosis. "
                f"{product_name} could be relevant as a possible support product, "
                f"but a qualified agricultural expert should confirm the issue first. "
                f"Please follow the official product label for any application or safety instructions."
            )

        return (
            f"The image looks similar to cases involving {crop} and {disease}, "
            f"but the confidence is not high enough for an automatic diagnosis. "
            f"Please ask a qualified agricultural expert to review the crop before applying any treatment."
        )

    if product_name and not weak_product_match:
        return (
            f"The image appears similar to {crop} cases involving {disease}. "
            f"{product_name} could be relevant as a possible support product, "
            f"but the diagnosis should still be confirmed before treatment. "
            f"Please follow the official product label for application and safety instructions."
        )

    return (
        f"The image appears similar to {crop} cases involving {disease}. "
        f"I could not identify a strong product recommendation from the available data. "
        f"Please confirm the diagnosis with a qualified agricultural expert before applying any treatment."
    )


# ==========================================
# MAIN ENTRYPOINT
# ==========================================

def diagnose_crop_image(
    image_path: str,
    user_text: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        result = hybrid_retrieve_for_image(
            image_path=image_path,
            user_text=user_text,
            image_k=config.retrieval.top_k,
            product_k=8,
            support_k=3,
        )

    except Exception as error:
        return {
            "success": False,
            "vision_used": True,
            "message": f"Vision diagnosis failed: {str(error)}",
            "diagnosis": None,
            "best_product": None,
            "recommended_products": [],
            "historical_cases": [],
            "similar_images": [],
            "response": (
                "I could not complete the image diagnosis. "
                "Please try again with a clear plant image or ask a qualified agricultural expert to review it."
            ),
        }

    if not result.get("success"):
        return {
            "success": False,
            "vision_used": True,
            "message": result.get("message", "Diagnosis failed."),
            "diagnosis": None,
            "best_product": None,
            "recommended_products": [],
            "historical_cases": [],
            "similar_images": [],
            "response": (
                "I could not find a confident match for this image. "
                "Please upload a clearer crop image or ask a qualified agricultural expert to review it."
            ),
        }

    response = _build_safe_vision_response(result)

    diagnosis = result.get("diagnosis", {})
    needs_human_review = diagnosis.get("needs_human_review", True)

    best_product = result.get("best_product")
    weak_product_match = _is_weak_product_match(best_product)

    # Customer-visible recommendation logic:
    # If diagnosis confidence is low OR product match is weak,
    # hide product recommendation from the main response payload.
    customer_visible_best_product = (
        None
        if needs_human_review or weak_product_match
        else best_product
    )

    customer_visible_products = (
        []
        if needs_human_review or weak_product_match
        else result.get("recommended_products", [])
    )

    return {
        "success": True,
        "vision_used": True,

        "diagnosis": result["diagnosis"],

        # Safe customer-visible fields
        "best_product": customer_visible_best_product,
        "recommended_products": customer_visible_products,

        # Debug/demo fields
        "debug_best_product": result.get("best_product"),
        "debug_recommended_products": result.get("recommended_products", []),

        "historical_cases": result.get("historical_cases", []),
        "similar_images": result.get("similar_images", []),
        "response": response,
        "retrieval_query": result.get("query"),
    }