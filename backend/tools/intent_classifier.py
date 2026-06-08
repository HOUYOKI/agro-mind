def has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def classify_intent(message: str) -> str:
    """
    Rule-based intent classifier for Agro-Mind MVP.

    Purpose:
    - Detect what the customer is asking for.
    - Route the message to the correct backend tool.
    - Keep logic explainable before adding RAG/LLM.
    """

    text = message.lower().strip()

    # ------------------------------------------------------------
    # 1. Safety-sensitive pesticide / human / pet exposure
    # ------------------------------------------------------------
    safety_keywords = [
        "eat it",
        "eaten",
        "eat after",
        "can it be eaten",
        "vegetables be eaten",
        "fruit be eaten",
        "after spraying",
        "spraying can",
        "how many days after spraying",
        "harvest",
        "harvested",
        "picked",
        "pick",
        "withdrawal period",
        "pre-harvest",
        "toxicity",
        "toxic",
        "poison",
        "poisoning",
        "die",
        "will i die",
        "dangerous",
        "accidentally ingest",
        "ingests",
        "ingested",
        "swallow",
        "drink",
        "skin burning",
        "eyes",
        "pet",
        "cat",
        "cats",
        "dog",
        "dogs",
        "ventilation",
        "ventilate",
        "volatilize",
        "used at home",
        "at home",
        "use it safely",
        "safely",
        "burns the flowers",
        "burn the flowers",
        "burns the fruits",
        "burn the fruits",
        "want to die",
        "do not want to live",
        "don't want to live",
        "life has no meaning",
        "bad mood",
        "unhappy",
    ]

    if has_any(text, safety_keywords):
        return "pesticide_safety"

    # ------------------------------------------------------------
    # 2. Complaint / after-sales issue
    # Put this before order/product/diagnosis because complaints
    # often include product/order words.
    # ------------------------------------------------------------
    complaint_keywords = [
        "refund",
        "compensation",
        "fake",
        "fake pesticide",
        "damaged",
        "leaked",
        "leak",
        "leaking",
        "none left",
        "almost none",
        "wrong item",
        "wrong product",
        "sent the wrong",
        "missing",
        "one bottle missing",
        "not received",
        "have not received",
        "did not receive",
        "cannot find it",
        "could not find it",
        "says it was received",
        "who received it",
        "how will you handle",
        "not effective",
        "no effect",
        "does not work",
        "didn't work",
        "did not work",
        "killed my crop",
        "crop died",
        "request a refund",
        "demand compensation",
        "resend",
        "send another",
        "return",
        "can i return",
    ]

    if has_any(text, complaint_keywords):
        return "complaint"

    # ------------------------------------------------------------
    # 3. Order / shipping / logistics
    # ------------------------------------------------------------
    order_keywords = [
        "order",
        "tracking",
        "delivery",
        "deliver",
        "shipped",
        "ship",
        "shipping",
        "courier",
        "postal courier",
        "package",
        "parcel",
        "goods",
        "arrive",
        "arrival",
        "how many days will this take",
        "how long will it take",
        "where does it ship from",
        "ship from",
        "has it shipped",
        "not shipped",
        "same place for a week",
        "where is my order",
    ]

    if has_any(text, order_keywords):
        return "order_status"

    # ------------------------------------------------------------
    # 4. Crop diagnosis / pest / disease
    # ------------------------------------------------------------
    diagnosis_keywords = [
        "mildew",
        "powdery mildew",
        "downy mildew",
        "root rot",
        "rotten roots",
        "roots are rotten",
        "red spider mites",
        "white mites",
        "spider mites",
        "white bugs",
        "bugs on my",
        "aphids",
        "pests",
        "disease",
        "yellow leaves",
        "leaves have",
        "leaves look",
        "leaf spots",
        "spots",
        "what is my case",
        "what type is my case",
        "which type",
        "what medicine should i use",
        "which product should i use",
        "fungus",
        "fungal",
        "blight",
        "lettuce roots",
        "kalanchoe",
        "strawberries have",
        "tomato",
        "crop issue",
        "what is going on with my plant",
        "what is wrong with my plant",
    ]

    if has_any(text, diagnosis_keywords):
        return "crop_diagnosis"

    # ------------------------------------------------------------
    # 5. Product usage / dosage / application / suitability
    # ------------------------------------------------------------
    product_keywords = [
        "how do i use",
        "how to use",
        "usage",
        "usage method",
        "main function",
        "function of this product",
        "dosage",
        "dose",
        "dilution",
        "dilution ratio",
        "ratio",
        "mix with water",
        "mixed with",
        "how much water",
        "how many jin",
        "how many grams",
        "how many ml",
        "grams mixed",
        "one bottle",
        "one pack",
        "spray",
        "sprayed",
        "used as a spray",
        "sprayer",
        "20-liter sprayer",
        "pour into the soil",
        "soil",
        "seed",
        "potato seed",
        "treat",
        "can it be used",
        "used on",
        "can this chemical",
        "can this herbicide",
        "herbicide",
        "chemical",
        "harm",
        "broad beans",
        "rapeseed",
        "mustard-type rapeseed",
        "which month",
        "best to use",
        "every day",
        "daily",
        "small tube",
        "buckets of water",
        "15mg",
        "1.5",
        "orchard",
        "weeding",
        "product",
        "ingredient",
        "ingredients",
        "application",
    ]

    if has_any(text, product_keywords):
        return "product_question"

    # ------------------------------------------------------------
    # 6. Human support
    # ------------------------------------------------------------
    human_keywords = [
        "human",
        "agent",
        "support",
        "representative",
        "customer service",
        "talk to someone",
    ]

    if has_any(text, human_keywords):
        return "human_support_needed"

    # ------------------------------------------------------------
    # 7. Follow-up
    # ------------------------------------------------------------
    follow_up_keywords = [
        "again",
        "still",
        "already",
        "before",
        "after that",
        "follow up",
    ]

    if has_any(text, follow_up_keywords):
        return "follow_up"

    return "general_question"