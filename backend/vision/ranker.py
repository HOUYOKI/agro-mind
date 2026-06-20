"""
Simple ranking layer for Agro-Mind vision retrieval.

Purpose:
- Prioritize products that match the detected crop/disease.
- Prefer closer vector matches.
- Avoid claiming the top product is a guaranteed treatment.
"""

from typing import List, Dict, Any


def _to_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(str(item) for item in value)

    return str(value)


def _contains(text: str, target: str) -> bool:
    if not text or not target:
        return False

    return target.lower() in text.lower()


def score_product(
    product: Dict[str, Any],
    crop: str,
    disease: str,
    disease_type: str = "",
) -> float:
    score = 0.0

    distance = product.get("distance")

    if distance is not None:
        try:
            score += max(0.0, 1.0 - float(distance))
        except Exception:
            pass

    crops_text = _to_text(product.get("crops"))
    diseases_text = _to_text(product.get("diseases"))
    product_type_text = _to_text(product.get("product_type"))

    if _contains(crops_text, crop):
        score += 0.35

    if _contains(diseases_text, disease):
        score += 0.45

    if disease_type and _contains(product_type_text, disease_type):
        score += 0.15

    if product.get("is_pesticide"):
        score += 0.05

    if product.get("is_microbial"):
        score += 0.03

    if product.get("is_fertilizer"):
        score += 0.02

    return round(score, 4)


def rank_products(
    products: List[Dict[str, Any]],
    crop: str,
    disease: str,
    disease_type: str = "",
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    ranked = []

    for product in products:
        product_copy = dict(product)
        product_copy["rank_score"] = score_product(
            product=product_copy,
            crop=crop,
            disease=disease,
            disease_type=disease_type,
        )
        ranked.append(product_copy)

    ranked.sort(
        key=lambda item: item.get("rank_score", 0),
        reverse=True,
    )

    return ranked[:top_k]


def pick_best_product(products: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    if not products:
        return None

    return products[0]