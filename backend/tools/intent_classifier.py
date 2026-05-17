def classify_intent(message: str) -> str:
    """
    Classifies the customer's message into a simple intent.
    This is keyword-based for the MVP.
    Later we can upgrade it to an LLM classifier.
    """

    message = message.lower()

    crop_keywords = [
        "leaf", "leaves", "spots", "yellow", "brown", "crop",
        "disease", "pest", "insect", "tomato", "plant", "fungus",
        "wilting", "curling", "aphid", "blight"
    ]

    product_keywords = [
        "product", "recommend", "use", "buy", "fungicide",
        "insecticide", "fertilizer", "pesticide"
    ]

    safety_keywords = [
        "poison", "drank", "child", "eyes", "skin", "burning",
        "vomiting", "pregnant", "mixed chemicals", "overdose",
        "sprayed too much"
    ]

    order_keywords = [
        "order", "delivery", "shipment", "tracking", "eta",
        "where is my order"
    ]

    complaint_keywords = [
        "complaint", "damaged", "refund", "bad service",
        "wrong product", "late", "angry"
    ]

    follow_up_keywords = [
        "follow up", "previous", "last case", "again", "same problem"
    ]

    human_support_keywords = [
        "human", "agent", "expert", "support", "call me", "talk to someone"
    ]

    if any(keyword in message for keyword in safety_keywords):
        return "pesticide_safety"

    if any(keyword in message for keyword in complaint_keywords):
        return "complaint"

    if any(keyword in message for keyword in order_keywords):
        return "order_status"

    if any(keyword in message for keyword in human_support_keywords):
        return "human_support_needed"

    if any(keyword in message for keyword in follow_up_keywords):
        return "follow_up"

    if any(keyword in message for keyword in crop_keywords):
        return "crop_diagnosis"

    if any(keyword in message for keyword in product_keywords):
        return "product_question"

    return "general_question"