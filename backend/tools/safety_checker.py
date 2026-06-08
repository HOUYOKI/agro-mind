def has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def check_safety(message: str, intent: str) -> dict:
    """
    Rule-based safety checker for Agro-Mind MVP.

    Important idea:
    Intent tells us the topic.
    Safety checks the risk level inside that topic.

    Example:
    - "How much water for one bottle?" = product_question + low risk
    - "Can this herbicide harm broad beans?" = product_question + medium risk
    - "Will I die if I eat it?" = pesticide_safety + high risk
    """

    text = message.lower().strip()

    # ------------------------------------------------------------
    # 1. HIGH RISK: human/pet ingestion, poisoning, self-harm,
    # severe exposure, or serious complaint.
    # ------------------------------------------------------------
    high_risk_keywords = [
        # Human ingestion / poisoning
        "will i die",
        "die if i eat",
        "if i eat it",
        "eat it",
        "accidentally ingest",
        "ingests",
        "ingested",
        "swallow",
        "drink",
        "poison",
        "poisoning",
        "toxic",
        "toxicity",
        "dangerous if a person",

        # Pet / child exposure
        "cats or dogs",
        "cat accidentally",
        "dog accidentally",
        "pet",
        "will they die",
        "child touched",
        "skin burning",
        "eyes",
        "vomiting",

        # Self-harm language
        "want to die",
        "do not want to live",
        "don't want to live",
        "life has no meaning",
        "self harm",
        "kill myself",

        # Serious complaint / business escalation
        "refund",
        "compensation",
        "fake pesticide",
        "fake",
        "leaked",
        "leak",
        "leaking",
        "wrong item",
        "wrong product",
        "sent the wrong",
        "missing",
        "one bottle missing",
        "not received",
        "have not received",
        "did not receive",
        "says it was received",
        "who received it",
        "how will you handle",
        "none left",
        "almost none",
        "resend",
        "return",
        "can i return",
        "not effective",
        "no effect",
        "does not work",
        "did not work",
        "didn't work",
        "killed my crop",
        "crop died",
    ]

    if intent == "complaint" or has_any(text, high_risk_keywords):
        return {
            "risk_level": "high",
            "reason": "Message involves safety danger, serious exposure, self-harm risk, or a complaint requiring human escalation.",
            "escalation_required": True,
        }

    # ------------------------------------------------------------
    # 2. MEDIUM RISK: pesticide safety, harvest interval,
    # ventilation, crop suitability, sensitive crop, overuse,
    # or dosage confusion.
    # ------------------------------------------------------------
    medium_risk_keywords = [
        # Harvest / residue / edible safety
        "after spraying",
        "spraying can",
        "vegetables be eaten",
        "fruit be eaten",
        "can it be eaten",
        "how many days",
        "harvest",
        "harvested",
        "picked",
        "pick",
        "withdrawal period",
        "pre-harvest",

        # Home use / ventilation / exposure prevention
        "ventilation",
        "ventilate",
        "volatilize",
        "used at home",
        "at home",
        "use it safely",
        "safely",
        "protective",
        "gloves",
        "mask",

        # Crop damage / phytotoxicity / sensitive crop
        "harm",
        "damage",
        "burn",
        "burns",
        "burn the flowers",
        "burns the flowers",
        "burn the fruits",
        "burns the fruits",
        "herbicide",
        "chemical",
        "can this chemical",
        "can this herbicide",
        "sprayed on rapeseed",
        "rapeseed",
        "mustard-type rapeseed",
        "broad beans",
        "tea trees",
        "orchard",
        "weeding in an orchard",

        # Repeated / risky application
        "every day",
        "daily",
        "sprayed every day",
        "spray every day",
        "how often",
        "repeat",
        "again and again",

        # Dosage confusion / conflicting measurement
        "3000 jin",
        "2000 jin",
        "15mg",
        "1.5",
        "small tube",
        "buckets of water",
        "too much",
        "too strong",
        "concentration",
        "wrong ratio",
        "confused",
    ]

    if intent == "pesticide_safety" or has_any(text, medium_risk_keywords):
        return {
            "risk_level": "medium",
            "reason": "Message involves pesticide safety, crop suitability, dosage uncertainty, or application risk.",
            "escalation_required": True,
        }

    # ------------------------------------------------------------
    # 3. MEDIUM RISK: crop diagnosis usually needs confirmation.
    # ------------------------------------------------------------
    crop_diagnosis_keywords = [
        "mildew",
        "powdery mildew",
        "downy mildew",
        "root rot",
        "rotten roots",
        "red spider mites",
        "white mites",
        "white bugs",
        "aphids",
        "pests",
        "disease",
        "yellow leaves",
        "leaves look",
        "leaves have",
        "spots",
        "what medicine should i use",
        "which product should i use",
        "what type is my case",
        "what is my case",
    ]

    if intent == "crop_diagnosis" or has_any(text, crop_diagnosis_keywords):
        return {
            "risk_level": "medium",
            "reason": "Crop diagnosis or product selection may require expert or image confirmation.",
            "escalation_required": True,
        }

    # ------------------------------------------------------------
    # 4. LOW RISK: normal product usage.
    # ------------------------------------------------------------
    if intent == "product_question":
        return {
            "risk_level": "low",
            "reason": "General product usage question with no detected safety hazard.",
            "escalation_required": False,
        }

    # ------------------------------------------------------------
    # 5. LOW RISK: normal logistics.
    # ------------------------------------------------------------
    if intent == "order_status":
        return {
            "risk_level": "low",
            "reason": "Logistics or order-status request with no safety risk detected.",
            "escalation_required": False,
        }

    return {
        "risk_level": "low",
        "reason": "No safety-sensitive issue detected.",
        "escalation_required": False,
    }