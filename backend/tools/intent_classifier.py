import os
import re
import requests


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("AGRO_MIND_TEXT_MODEL", "qwen2.5:7b-instruct")


# These are the labels agent_graph.py understands.
GRAPH_INTENTS = [
    "crop_diagnosis",
    "product_question",
    "pesticide_safety",
    "order_status",
    "complaint",
    "general_question",
]


# Extra labels are allowed from Qwen, but normalized before returning.
VALID_INTENTS = [
    "crop_diagnosis",
    "vision_analysis",
    "product_recommendation",
    "product_information",
    "product_question",
    "pesticide_safety",
    "order_status",
    "complaint",
    "customer_profile",
    "agriculture_knowledge",
    "general_question",
]


INTENT_NORMALIZATION = {
    "product_recommendation": "product_question",
    "product_information": "product_question",
    "product_question": "product_question",
    "agriculture_knowledge": "general_question",
    "vision_analysis": "general_question",
    "customer_profile": "general_question",
    "crop_diagnosis": "crop_diagnosis",
    "pesticide_safety": "pesticide_safety",
    "order_status": "order_status",
    "complaint": "complaint",
    "general_question": "general_question",
}


def normalize_intent(intent: str) -> str:
    intent = (intent or "").strip().lower()
    return INTENT_NORMALIZATION.get(intent, "general_question")


def qwen_fallback(user_query: str) -> str:
    """
    Hybrid fallback:
    Rule-based intent runs first.
    Qwen is only used when no rule matches.
    Timeout is low to avoid latency.
    """
    prompt = f"""
Classify the user query into exactly one label.

Valid labels:
{chr(10).join(VALID_INTENTS)}

User Query:
{user_query}

Output ONLY one label.
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 5,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=3,
        )
        response.raise_for_status()

        output = response.json().get("response", "").strip().lower()

        for intent in VALID_INTENTS:
            if intent in output:
                return normalize_intent(intent)

    except Exception:
        pass

    return "general_question"


def classify_intent(user_query: str) -> str:
    query = (user_query or "").lower().strip()
    query = re.sub(r"\s+", " ", query)

    if not query:
        return "general_question"

    # 1. Complaint must come before order/product/crop.
    complaint_phrases = [
        "complaint",
        "refund",
        "compensation",
        "fake",
        "scam",
        "fraud",
        "bad product",
        "poor quality",
        "defective",
        "damaged my crops",
        "damaged my plants",
        "damaged my plant",
        "ruined my crops",
        "ruined my plants",
        "killed my crops",
        "killed my plants",
        "burned my plants",
        "burnt my plants",
        "caused losses",
        "caused damage",
        "unhappy",
        "not happy",
        "not satisfied",
        "dissatisfied",
        "report a problem",
        "problem with my order",
        "problem with your product",
        "legal",
        "lawsuit",
        "sue",

        # Chinese complaint terms
        "投诉",
        "退款",
        "赔偿",
        "假产品",
        "损坏了我的作物",
        "毁了我的作物",
        "杀死了我的作物",
        "烧伤了植物",
        "烧苗",
        "起诉",
    ]

    if any(phrase in query for phrase in complaint_phrases):
        return "complaint"

    # 2. Safety must come before crop/product.
    pesticide_safety_phrases = [
        "toxicity",
        "toxic",
        "poison",
        "poisoning",
        "swallowed",
        "ingested",
        "drank pesticide",
        "drink pesticide",
        "ate pesticide",
        "inhaled pesticide",
        "inhaled chemical",
        "pesticide spray",
        "pesticide got into my eyes",
        "pesticide got into my eye",
        "pesticide in my eyes",
        "pesticide in my eye",
        "chemical in my eyes",
        "chemical in my eye",
        "eyes",
        "eye",
        "skin exposure",
        "pesticide on my skin",
        "chemical exposure",
        "pesticide exposure",
        "safe to eat",
        "can i eat",
        "eat after spraying",
        "after spraying pesticide",
        "after spraying",
        "food safety",
        "harvest interval",
        "reentry interval",
        "pesticide residue",
        "residue dangerous",
        "is pesticide residue dangerous",
        "ppe",
        "gloves",
        "mask",
        "kill myself",
        "suicide",
        "self harm",
        "self-harm",
        "harm myself",

        # Chinese safety terms
        "误食",
        "喝了农药",
        "吞了农药",
        "吃了农药",
        "农药中毒",
        "中毒",
        "农药进眼睛",
        "农药进眼",
        "化学品进眼睛",
        "吸入农药",
        "吸入化学品",
        "喷药后",
        "可以吃吗",
        "能吃吗",
        "安全间隔期",
        "自杀",
        "自残",
    ]

    if any(phrase in query for phrase in pesticide_safety_phrases):
        return "pesticide_safety"

    # 3. Product-question wording should beat crop diagnosis.
    product_question_phrases = [
        "which product",
        "what product",
        "recommend",
        "recommendation",
        "suggest",
        "best product",
        "product helps",
        "product can help",
        "helps tomato",
        "helps crop",
        "suitable for",
        "which fungicide",
        "what fungicide",
        "which fertilizer",
        "what fertilizer",
        "fungicide is suitable",
        "product for",
        "ingredient",
        "ingredients",
        "product information",
        "active ingredient",
        "dosage",
        "dose",
        "dilution",
        "mix",
        "how many ml",
        "how much",
    ]

    if any(phrase in query for phrase in product_question_phrases):
        return "product_question"

    # 4. Order status.
    order_phrases = [
        "order",
        "tracking",
        "track my order",
        "shipment",
        "shipping",
        "delivery",
        "delivered",
        "package",
        "eta",
        "where is my order",
        "order status",
        "tracking information",
        "has my shipment arrived",
    ]

    if any(phrase in query for phrase in order_phrases):
        return "order_status"

    # 5. Crop diagnosis.
    crop_phrases = [
        "disease",
        "symptom",
        "symptoms",
        "diagnosis",
        "treatment",
        "leaf",
        "leaves",
        "yellow leaves",
        "yellowing",
        "turning yellow",
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
        "watermelon",
        "garlic",
        "crop",
        "plant problem",
        "plant disease",
    ]

    if any(phrase in query for phrase in crop_phrases):
        return "crop_diagnosis"

    return qwen_fallback(user_query)


if __name__ == "__main__":
    tests = [
        "My tomato leaves have black spots",
        "My pepper leaves are turning yellow",
        "Which product helps tomato diseases?",
        "Recommend a product for powdery mildew",
        "What product can help leaf spot disease?",
        "Which fungicide is suitable for tomatoes?",
        "Suggest a product for crop disease management",
        "I accidentally swallowed pesticide",
        "Pesticide got into my eyes",
        "Is pesticide residue dangerous?",
        "Where is order 1001?",
        "I am unhappy with your product",
        "I want to report a problem with my order",
        "Hello",
    ]

    for test in tests:
        print(test)
        print("->", classify_intent(test))
        print("-" * 50)