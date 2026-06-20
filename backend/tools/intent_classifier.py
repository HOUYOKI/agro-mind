import re
import requests


def classify_intent(user_query: str) -> str:
    """
    Hybrid intent classifier for Agro-Mind.
    Uses deterministic rules first, then local Qwen as backup.
    """
    query_clean = user_query.lower().strip()

    valid_intents = [
        "crop_diagnosis",
        "product_question",
        "pesticide_safety",
        "order_status",
        "complaint",
        "general_question"
    ]

    # 1. Complaint / human escalation signals
    complaint_keywords = [
        "fake",
        "scam",
        "fraud",
        "complaint",
        "refund",
        "compensation",
        "bad product",
        "defective",
        "damaged my crops",
        "damaged my crop",
        "ruined my crops",
        "ruined my crop",
        "killed my crops",
        "killed my plants",
        "burned my plants",
        "harmed my crops",
        "not working",
        "doesn't work",
        "did not work",
        "angry",
        "unacceptable"
    ]

    if any(keyword in query_clean for keyword in complaint_keywords):
        return "complaint"

    # 2. Order / logistics
    order_keywords = [
        "order",
        "tracking",
        "shipment",
        "shipping",
        "delivery",
        "delivered",
        "where is my order",
        "eta",
        "arrive",
        "package"
    ]

    if any(keyword in query_clean for keyword in order_keywords):
        return "order_status"

    # 3. Pesticide safety
    safety_keywords = [
        "pesticide on my skin",
        "skin",
        "eyes",
        "eye",
        "burning",
        "breathed",
        "inhaled",
        "swallowed",
        "drank",
        "ate pesticide",
        "poison",
        "toxicity",
        "toxic",
        "safety",
        "after spraying",
        "sprayed",
        "chemical exposure",
        "ppe",
        "gloves",
        "mask"
    ]

    if any(keyword in query_clean for keyword in safety_keywords):
        return "pesticide_safety"

    # 4. Crop diagnosis
    diagnostic_keywords = [
        "symptom",
        "treatment",
        "yellowing",
        "yellow leaves",
        "disease",
        "pest",
        "rot",
        "leaf",
        "leaves",
        "wilt",
        "citrus",
        "tomato",
        "spots",
        "blight",
        "mold",
        "fungus"
    ]

    if any(keyword in query_clean for keyword in diagnostic_keywords):
        return "crop_diagnosis"

    # 5. Product question
    product_keywords = [
        "product",
        "fertilizer",
        "dosage",
        "dose",
        "dilution",
        "how many ml",
        "how much",
        "spray",
        "use this",
        "ingredient",
        "mix"
    ]

    if any(keyword in query_clean for keyword in product_keywords):
        return "product_question"

    # 6. Qwen backup
    url = "http://127.0.0.1:11434/api/generate"

    prompt = f"""You are an intent classification engine for an agricultural AI system.

Map the user query to exactly one label.

VALID LABELS:
- crop_diagnosis: plant diseases, crop symptoms, pests, yellow leaves, plant treatments.
- product_question: product usage, fertilizers, pesticide dosage, ingredients, dilution.
- pesticide_safety: chemical toxicity, pesticide exposure, skin/eye contact, ingestion, PPE, food safety after spraying.
- order_status: shipping, logistics, order tracking, delivery.
- complaint: fake product, damaged crops, refund, compensation, angry customer, product did not work.
- general_question: greetings, casual talk, or unclear query.

Output ONLY the exact label.

User Query: "{user_query}"
Label:"""

    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 10
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=60)

        if response.status_code == 200:
            raw_output = response.json().get("response", "").strip().lower()
            extracted_words = re.findall(r"[a-z_]+", raw_output)

            for word in extracted_words:
                if word in valid_intents:
                    return word

    except requests.exceptions.RequestException:
        pass

    return "general_question"