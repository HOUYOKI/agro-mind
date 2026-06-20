import requests

VALID_INTENTS = [
    "crop_diagnosis",
    "product_question",
    "pesticide_safety",
    "order_status",
    "complaint",
    "general_question"
]

INTENT_KEYWORDS = {

    "complaint": [
        "complaint",
        "refund",
        "compensation",
        "fake",
        "scam",
        "fraud",
        "unhappy",
        "disappointed",
        "not satisfied",
        "dissatisfied",
        "bad product",
        "poor quality",
        "defective",
        "issue with product",
        "product issue",
        "problem with my order",
        "report a problem",
        "report issue",
        "angry",
        "unacceptable",
        "damaged my crops",
        "damaged my crop",
        "damaged my plants",
        "damaged plants",
        "ruined my crops",
        "ruined my crop",
        "killed my crops",
        "killed my plants",
        "burned my plants",
        "caused losses",
        "recommendation caused losses"
    ],

    "pesticide_safety": [
        "pesticide",
        "toxicity",
        "toxic",
        "poison",
        "swallowed",
        "inhaled",
        "breathed",
        "eyes",
        "eye",
        "skin",
        "chemical exposure",
        "after spraying",
        "sprayed",
        "eat after spraying",
        "residue",
        "spray residue",
        "residue on food",
        "dangerous",
        "safe to eat",
        "food safety",
        "harvest interval",
        "reentry interval",
        "ppe",
        "gloves",
        "mask"
    ],

    "product_question": [
        "product",
        "recommend",
        "recommendation",
        "help",
        "which product",
        "what product",
        "suggest",
        "fungicide",
        "fertilizer",
        "dosage",
        "dose",
        "dilution",
        "ingredient",
        "mix",
        "how much",
        "how many ml"
    ],

    "order_status": [
        "order",
        "tracking",
        "shipment",
        "shipping",
        "delivery",
        "delivered",
        "package",
        "eta",
        "where is my order",
        "track my order"
    ],

    "crop_diagnosis": [
        "disease",
        "symptom",
        "symptoms",
        "treatment",
        "yellow leaves",
        "yellowing",
        "leaf",
        "leaves",
        "spots",
        "leaf spot",
        "blight",
        "mildew",
        "fungus",
        "fungal",
        "rot",
        "wilt",
        "wilting",
        "pest",
        "tomato",
        "pepper",
        "cucumber",
        "rice",
        "citrus",
        "grape",
        "apple",
        "crop"
    ]
}


def qwen_fallback(user_query: str) -> str:

    prompt = f"""
Classify the user query into exactly one label.

Valid labels:
crop_diagnosis
product_question
pesticide_safety
order_status
complaint
general_question

User Query:
{user_query}

Output only one label.
"""

    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 5
        }
    }

    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json=payload,
            timeout=15
        )

        if response.status_code == 200:

            output = response.json().get(
                "response",
                ""
            ).strip().lower()

            for intent in VALID_INTENTS:
                if intent in output:
                    return intent

    except Exception:
        pass

    return "general_question"


def classify_intent(user_query: str) -> str:

    query = user_query.lower().strip()

    scores = {
        "crop_diagnosis": 0,
        "product_question": 0,
        "pesticide_safety": 0,
        "order_status": 0,
        "complaint": 0
    }

    for intent, keywords in INTENT_KEYWORDS.items():

        for keyword in keywords:

            if keyword in query:
                scores[intent] += 1

    best_intent = max(scores, key=scores.get)

    if scores[best_intent] > 0:
        return best_intent

    return qwen_fallback(user_query)