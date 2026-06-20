import os
import requests


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("AGRO_MIND_TEXT_MODEL", "qwen2.5:7b-instruct")


def check_safety(user_query: str, intent: str) -> dict:
    """
    Safety checker for Agro-Mind.

    Priority:
    1. Deterministic high-risk checks.
    2. Deterministic medium-risk checks.
    3. Complaint checks.
    4. Short Qwen fallback for unusual unsafe phrasing.
    5. Safe default.
    """
    text = (user_query or "").lower().strip()

    high_risk_keywords = [
        # Self-harm / poison
        "eat poison",
        "consume poison",
        "drink poison",
        "poison myself",
        "harm myself",
        "kill myself",
        "suicide",
        "self harm",
        "self-harm",

        # Pesticide ingestion
        "swallowed",
        "drank pesticide",
        "drink pesticide",
        "ate pesticide",
        "ingested",
        "poison",
        "poisoning",

        # Eye exposure
        "pesticide in my eyes",
        "pesticide in my eye",
        "chemical in my eyes",
        "chemical in my eye",
        "pesticide got into my eyes",
        "pesticide got into my eye",
        "chemical got into my eyes",
        "chemical got into my eye",
        "got into my eyes",
        "got into my eye",
        "splashed into my eyes",
        "splashed into my eye",
        "eye exposure",
        "eyes burning",
        "eye burning",

        # Mouth exposure
        "pesticide in my mouth",
        "chemical in my mouth",

        # Breathing exposure
        "inhaled pesticide",
        "inhaled chemical",
        "breathed pesticide",
        "breathed chemical",
        "can't breathe",
        "cannot breathe",
        "difficulty breathing",

        # Severe symptoms
        "vomiting",
        "dizzy",
        "faint",
        "unconscious",
        "severe pain",

        # Child / pet / livestock exposure
        "child swallowed",
        "baby swallowed",
        "child drank",
        "baby drank",
        "pet ate",
        "dog ate",
        "cat ate",
        "livestock ate",
        "cow ate",
        "goat ate",
        "sheep ate",

        # Chinese
        "误食",
        "喝了农药",
        "吞了农药",
        "吃了农药",
        "农药中毒",
        "中毒",
        "吃毒药",
        "喝毒药",
        "想吃毒药",
        "想喝毒药",
        "服毒",
        "毒死自己",
        "伤害自己",
        "自杀",
        "自残",
        "农药进眼睛",
        "农药进眼",
        "化学品进眼睛",
        "眼睛灼烧",
        "吸入农药",
        "吸入化学品",
        "呼吸困难",
        "不能呼吸",
        "呕吐",
        "头晕",
        "昏迷",
        "孩子喝了",
        "儿童喝了",
        "宝宝喝了",
        "宠物吃了",
        "狗吃了",
        "猫吃了",
        "牲畜吃了",
    ]

    if any(keyword in text for keyword in high_risk_keywords):
        return {
            "risk_level": "high",
            "reason": (
                "High-risk poison, pesticide exposure, self-harm, child/pet/livestock "
                "exposure, or severe symptom detected."
            ),
            "escalation_required": True,
        }

    medium_risk_keywords = [
        # English contact / exposure / food safety after pesticide
        "skin",
        "on my hand",
        "on my hands",
        "touched pesticide",
        "got pesticide on",
        "pesticide on my skin",
        "chemical on my skin",
        "splashed on me",
        "after spraying",
        "one day after spraying",
        "spraying accident",
        "exposure",
        "contact with pesticide",
        "rash after pesticide",
        "burning after spraying",
        "smell pesticide",
        "strong pesticide smell",
        "can i eat",
        "safe to eat",
        "harvest after spraying",
        "harvest interval",
        "reentry interval",
        "pesticide residue",
        "residue dangerous",
        "residue",

        # Chinese contact / exposure / food safety
        "皮肤接触",
        "农药碰到皮肤",
        "农药弄到手",
        "化学品弄到皮肤",
        "喷药后",
        "喷洒后",
        "接触农药",
        "农药暴露",
        "喷药事故",
        "可以吃吗",
        "能吃吗",
        "喷药后采收",
        "安全间隔期",
    ]

    if any(keyword in text for keyword in medium_risk_keywords):
        return {
            "risk_level": "medium",
            "reason": (
                "Pesticide contact, exposure, or food-safety timing question detected. "
                "Human review may be needed."
            ),
            "escalation_required": True,
        }

    complaint_keywords = [
        # English complaints
        "damaged my crops",
        "ruined my crops",
        "killed my crops",
        "burned my plants",
        "burnt my plants",
        "fake product",
        "complaint",
        "refund",
        "compensation",
        "legal",
        "sue",
        "lawsuit",
        "unhappy",
        "not happy",
        "not satisfied",
        "dissatisfied",
        "report a problem",
        "problem with my order",
        "problem with your product",

        # Chinese complaints
        "损坏了我的作物",
        "毁了我的作物",
        "杀死了我的作物",
        "烧伤了植物",
        "烧苗",
        "假产品",
        "投诉",
        "退款",
        "赔偿",
        "法律",
        "起诉",
    ]

    if any(keyword in text for keyword in complaint_keywords):
        return {
            "risk_level": "medium",
            "reason": (
                "Customer complaint, crop damage claim, refund/legal issue, or "
                "compensation-sensitive case requires human review."
            ),
            "escalation_required": True,
        }

    prompt = f"""You are a strict safety guardrail for an agricultural AI system.

Classify the user query as UNSAFE if it contains:
- poison ingestion
- self-harm
- pesticide or chemical ingestion
- pesticide or chemical exposure to skin, eyes, breathing, child, pet, or livestock
- crop damage complaint caused by product use
- dangerous chemical misuse
- legal complaint, refund demand, or compensation claim
- pesticide food safety question such as eating or harvesting soon after spraying

Otherwise classify as SAFE.

Output only SAFE or UNSAFE.

User Query: "{user_query}"
Intent: "{intent}"
Result:"""

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
        result = response.json().get("response", "").strip().upper()

        if "UNSAFE" in result:
            return {
                "risk_level": "high",
                "reason": "Safety policy violation detected by safety guardrail.",
                "escalation_required": True,
            }

    except Exception:
        pass

    return {
        "risk_level": "low",
        "reason": "Safe.",
        "escalation_required": False,
    }