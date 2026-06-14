import requests


def check_safety(user_query: str, intent: str) -> dict:
    """
    Safety checker for Agro-Mind.
    Deterministic safety rules first, then Qwen backup.
    """
    text = user_query.lower().strip()

    # High-risk human/pet/livestock exposure
    high_risk_keywords = [
        "swallowed",
        "drank",
        "drink pesticide",
        "ate pesticide",
        "ingested",
        "poison",
        "poisoning",
        "pesticide in my eyes",
        "splashed into my eyes",
        "eye",
        "eyes",
        "inhaled",
        "breathed",
        "breathing",
        "can't breathe",
        "vomiting",
        "dizzy",
        "faint",
        "unconscious",
        "burning",
        "severe pain",
        "child",
        "baby",
        "pet ate",
        "dog ate",
        "cat ate",
        "livestock ate",
        "cow ate",
        "goat ate",
        "sheep ate",
        "suicide",
        "self harm",
        "kill myself"
    ]

    if any(keyword in text for keyword in high_risk_keywords):
        return {
            "risk_level": "high",
            "reason": "High-risk pesticide or chemical exposure detected. Human expert or medical review is required.",
            "escalation_required": True
        }

    # Medium-risk contact/exposure
    medium_risk_keywords = [
        "skin",
        "on my hand",
        "on my hands",
        "touched pesticide",
        "got pesticide on",
        "pesticide on my skin",
        "chemical on my skin",
        "splashed on me",
        "after spraying",
        "spraying accident",
        "exposure",
        "contact with pesticide"
    ]

    if any(keyword in text for keyword in medium_risk_keywords):
        return {
            "risk_level": "medium",
            "reason": "Pesticide contact or exposure detected. First-aid guidance and human review may be needed.",
            "escalation_required": True
        }

    # Complaint/crop damage should not be treated as low-normal support
    complaint_keywords = [
        "damaged my crops",
        "ruined my crops",
        "killed my crops",
        "burned my plants",
        "fake product",
        "complaint",
        "refund",
        "compensation"
    ]

    if any(keyword in text for keyword in complaint_keywords):
        return {
            "risk_level": "medium",
            "reason": "Customer complaint or crop damage claim requires human review.",
            "escalation_required": True
        }

    # Qwen backup for unusual unsafe queries
    url = "http://127.0.0.1:11434/api/generate"

    prompt = f"""You are a strict safety guardrail for an agricultural AI system.

Classify the user query as UNSAFE if it contains:
- pesticide/chemical ingestion
- pesticide/chemical exposure to skin, eyes, breathing, child, pet, or livestock
- self-harm
- crop damage complaint caused by product use
- dangerous chemical misuse

Otherwise classify as SAFE.

Output only SAFE or UNSAFE.

User Query: "{user_query}"
Result:"""

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
        response = requests.post(url, json=payload, timeout=8)
        result = response.json().get("response", "").strip().upper()

        if "UNSAFE" in result:
            return {
                "risk_level": "high",
                "reason": "Safety policy violation detected by safety guardrail.",
                "escalation_required": True
            }

    except Exception:
        pass

    return {
        "risk_level": "low",
        "reason": "Safe.",
        "escalation_required": False
    }