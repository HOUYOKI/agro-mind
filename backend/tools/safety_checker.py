def check_safety(message: str, intent: str) -> dict:
    """
    Checks if the customer's message contains safety risks.
    For MVP, this uses simple keyword rules.
    """

    message = message.lower()

    high_risk_keywords = [
        "poison",
        "drank pesticide",
        "drank",
        "child exposed",
        "child touched",
        "eyes",
        "skin burning",
        "burning",
        "vomiting",
        "pregnant",
        "mixed chemicals",
        "overdose",
        "sprayed too much",
        "animal died",
        "crop destroyed",
        "legal complaint"
    ]

    medium_risk_keywords = [
        "pesticide",
        "chemical",
        "fungicide",
        "insecticide",
        "dosage",
        "how much",
        "spray",
        "apply"
    ]

    if any(keyword in message for keyword in high_risk_keywords):
        return {
            "risk_level": "high",
            "escalation_required": True,
            "reason": "Possible pesticide exposure or serious safety issue."
        }

    if intent == "complaint":
        return {
            "risk_level": "high",
            "escalation_required": True,
            "reason": "Customer complaint requires human review."
        }

    if any(keyword in message for keyword in medium_risk_keywords):
        return {
            "risk_level": "medium",
            "escalation_required": True,
            "reason": "Pesticide or chemical-related question requires careful guidance."
        }

    if intent == "crop_diagnosis":
        return {
            "risk_level": "medium",
            "escalation_required": True,
            "reason": "Crop diagnosis may require expert or image confirmation."
        }

    return {
        "risk_level": "low",
        "escalation_required": False,
        "reason": "No major safety risk detected."
    }