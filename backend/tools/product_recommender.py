import pandas as pd
from pathlib import Path


PRODUCTS_FILE = Path(__file__).resolve().parent.parent / "data" / "products.csv"


def detect_crop_and_issue(message: str) -> dict:
    """
    Very simple crop/issue detector for MVP.
    Later we can replace this with an LLM or RAG-based extractor.
    """

    message = message.lower()

    crop = "General"
    issue = "Unknown"

    if "tomato" in message:
        crop = "Tomato"
    elif "citrus" in message or "orange" in message or "lemon" in message:
        crop = "Citrus"
    elif "palm" in message:
        crop = "Palm"

    if "yellow" in message or "brown spots" in message or "spots" in message or "blight" in message:
        issue = "Early Blight"
    elif "aphid" in message or "insect" in message or "bugs" in message:
        issue = "Aphids"
    elif "nutrient" in message or "deficiency" in message or "weak leaves" in message:
        issue = "Nutrient Deficiency"
    elif "weevil" in message:
        issue = "Red Palm Weevil"
    elif "fungal" in message or "fungus" in message:
        issue = "Fungal Spots"

    return {
        "crop": crop,
        "issue": issue
    }


def recommend_product(message: str) -> dict:
    """
    Recommends a product from products.csv based on simple crop and issue matching.
    """

    detected = detect_crop_and_issue(message)
    crop = detected["crop"]
    issue = detected["issue"]

    try:
        products = pd.read_csv(PRODUCTS_FILE)
    except FileNotFoundError:
        return {
            "recommended_product": None,
            "product_id": None,
            "reason": "products.csv file was not found.",
            "safety_note": "No safety note available.",
            "detected_crop": crop,
            "detected_issue": issue
        }

    exact_match = products[
        (products["crop"].str.lower() == crop.lower()) &
        (products["target_issue"].str.lower() == issue.lower())
    ]

    if not exact_match.empty:
        product = exact_match.iloc[0]

        return {
            "recommended_product": product["name"],
            "product_id": product["product_id"],
            "reason": f"Matched crop '{crop}' with issue '{issue}'.",
            "safety_note": product["safety_note"],
            "detected_crop": crop,
            "detected_issue": issue
        }

    fallback = products[products["crop"].str.lower() == "general"]

    if not fallback.empty:
        product = fallback.iloc[0]

        return {
            "recommended_product": product["name"],
            "product_id": product["product_id"],
            "reason": "No exact match found. Using general support product.",
            "safety_note": product["safety_note"],
            "detected_crop": crop,
            "detected_issue": issue
        }

    return {
        "recommended_product": None,
        "product_id": None,
        "reason": "No suitable product found. Human expert review required.",
        "safety_note": "Do not apply pesticide without expert confirmation.",
        "detected_crop": crop,
        "detected_issue": issue
    }