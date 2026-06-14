import requests
import json
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

HIGH_RISK_KEYWORDS = [
    "poison", "poisoning", "chemical exposure", "overdose", "dizzy",
    "vomiting", "difficulty breathing", "emergency", "toxic",
    "accidentally mixed pesticides", "pesticide overdose", "skin burn", "eye irritation",
]

def build_escalation_payload(user_query: str, customer_id: str, intent: str, risk_level: str, category: str, reason: str):
    return {
        "status": "ESCALATION_TRIGGERED",
        "timestamp": datetime.utcnow().isoformat(),
        "customer_id": customer_id,
        "user_query": user_query,
        "intent": intent,
        "risk_level": risk_level,
        "category": category,
        "reason": reason,
        "action": "SEND_TO_HUMAN_AGENT",
    }

def escalate_case(user_query: str, customer_id: str = None, intent: str = None, context: dict = None) -> dict:
    context = context or {}
    query_lower = user_query.lower()

    if any(keyword in query_lower for keyword in HIGH_RISK_KEYWORDS):
        return build_escalation_payload(
            user_query=user_query, customer_id=customer_id, intent=intent,
            risk_level="critical", category="medical_risk", reason="High-risk safety keyword detected."
        )

    confidence = context.get("confidence")
    if confidence is not None and confidence < 0.50:
        return build_escalation_payload(
            user_query=user_query, customer_id=customer_id, intent=intent,
            risk_level="medium", category="unknown", reason="Diagnosis confidence below threshold."
        )

    prompt = f"""
You are a Safety & Escalation Agent for Agro-Mind.
Analyze the case and determine if escalation to a human expert is required.
You must return ONLY valid JSON.

Schema:
{{
  "escalate": true,
  "reason": "text",
  "risk_level": "low|medium|high|critical",
  "category": "safety|pesticide_misuse|complaint|medical_risk|unknown|other",
  "confidence": 0.5
}}

User Query: {user_query}
Intent: {intent}
Context: {json.dumps(context)}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        result_text = response.json().get("response", "{}").strip()
        
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()

        result = json.loads(result_text)
        escalate = result.get("escalate", False)
        
        if escalate:
            return build_escalation_payload(
                user_query=user_query, customer_id=customer_id, intent=intent,
                risk_level=result.get("risk_level", "medium"),
                category=result.get("category", "unknown"),
                reason=result.get("reason", "Escalation recommended by Safety Agent.")
            )

        return {
            "status": "SAFE",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "No escalation required.",
            "agent_confidence": result.get("confidence", 1.0),
        }

    except Exception as e:
        return {
            "status": "ESCALATION_TRIGGERED",
            "timestamp": datetime.utcnow().isoformat(),
            "customer_id": customer_id,
            "user_query": user_query,
            "intent": intent,
            "risk_level": "high",
            "category": "system_failure",
            "reason": f"Safety agent error: {str(e)}",
            "action": "SEND_TO_HUMAN_AGENT",
        }

if __name__ == '__main__':
    print("\n==================================================")
    print("   Running tool check in isolated path...")
    print("==================================================")
    
    query_test = "I accidentally swallowed some fertilizer and now I feel dizzy."
    print(f'Incoming query: "{query_test}"')
    
    final_output = escalate_case(user_query=query_test, customer_id="farmer_789", intent="pesticide_issue")
    
    print("\nOutput result:")
    print(json.dumps(final_output, indent=2, ensure_ascii=False))
    print("==================================================\n")