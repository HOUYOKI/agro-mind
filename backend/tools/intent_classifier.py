import re
import requests

VALID_INTENTS = [
    "crop_diagnosis",
    "vision_analysis",
    "product_recommendation",
    "product_information",
    "pesticide_safety",
    "order_status",
    "complaint",
    "customer_profile",
    "agriculture_knowledge",
    "general_question"
]

INTENT_KEYWORDS = {

    "complaint": [
        "complaint", "refund", "compensation",
        "fake", "scam", "fraud",
        "bad product", "poor quality",
        "defective",
        "damaged my crops",
        "damaged my plants",
        "ruined my crops",
        "killed my crops",
        "burned my plants",
        "angry",
        "not satisfied",
        "dissatisfied",
        "caused losses"
    ],

    "pesticide_safety": [
        "pesticide",
        "toxicity",
        "toxic",
        "poison",
        "poisoning",
        "swallowed",
        "inhaled",
        "chemical exposure",
        "skin",
        "eye",
        "eyes",
        "safe to eat",
        "eat after spraying",
        "food safety",
        "harvest interval",
        "reentry interval",
        "ppe",
        "gloves",
        "mask"
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
        "track my order",
        "where is my order"
    ],

    "vision_analysis": [
        "image",
        "photo",
        "picture",
        "upload image",
        "analyze image",
        "analyze this image",
        "leaf image",
        "plant image",
        "uploaded image",
        "see this image"
    ],

    "customer_profile": [
        "my profile",
        "customer profile",
        "previous orders",
        "my orders",
        "order history",
        "support history",
        "my history",
        "my account"
    ],

    "product_information": [
        "ingredient",
        "ingredients",
        "product information",
        "label",
        "active ingredient",
        "dosage",
        "dose",
        "dilution",
        "mix",
        "how many ml",
        "how much"
    ],

    "product_recommendation": [
        "recommend",
        "recommendation",
        "suggest",
        "which product",
        "what product",
        "best product",
        "fungicide",
        "fertilizer",
        "pesticide product"
    ],

    "crop_diagnosis": [
        "disease",
        "symptom",
        "symptoms",
        "diagnosis",
        "treatment",
        "leaf",
        "leaves",
        "yellow leaves",
        "yellowing",
        "spots",
        "black spots",
        "brown spots",
        "leaf spot",
        "blight",
        "early blight",
        "late blight",
        "powdery mildew",
        "downy mildew",
        "mildew",
        "fungus",
        "fungal",
        "rot",
        "root rot",
        "wilt",
        "wilting",
        "aphid",
        "aphids",
        "whitefly",
        "whiteflies",
        "thrips",
        "spider mites",
        "pest",
        "pests",
        "tomato",
        "pepper",
        "cucumber",
        "rice",
        "citrus",
        "grape",
        "apple",
        "strawberry",
        "crop"
    ],

    "agriculture_knowledge": [
        "what causes",
        "how does",
        "why does",
        "best practice",
        "agriculture",
        "farming",
        "irrigation",
        "soil",
        "nutrient",
        "fertility",
        "crop management"
    ]
}


def qwen_fallback(user_query: str) -> str:

    prompt = f"""
Classify the user query into exactly one label.

Valid labels:
{chr(10).join(VALID_INTENTS)}

User Query:
{user_query}

Output ONLY one label.
"""

    payload = {
        "model": "qwen2.5:7b-instruct",
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
            timeout=10
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
    query = re.sub(r"\s+", " ", query)

    # High-priority intents

    if any(k in query for k in INTENT_KEYWORDS["complaint"]):
        return "complaint"

    if any(k in query for k in INTENT_KEYWORDS["pesticide_safety"]):
        return "pesticide_safety"

    scores = {}

    for intent in VALID_INTENTS:

        if intent == "general_question":
            continue

        scores[intent] = 0

        for keyword in INTENT_KEYWORDS.get(intent, []):

            if keyword in query:
                scores[intent] += 1

    best_intent = max(scores, key=scores.get)

    if scores[best_intent] > 0:
        return best_intent

    return qwen_fallback(user_query)


if __name__ == "__main__":

    tests = [
        "My tomato leaves have black spots",
        "Analyze this image of my tomato plant",
        "Recommend a fungicide for citrus canker",
        "What are the ingredients of Kairun?",
        "Is it safe to eat tomatoes after spraying?",
        "Where is my order?",
        "I want a refund",
        "Show my previous orders",
        "What causes powdery mildew?",
        "Hello"
    ]

    for t in tests:
        print(t)
        print("->", classify_intent(t))
        print("-" * 50)