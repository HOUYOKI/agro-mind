import requests
import json
import os

def check_safety(user_query: str, intent: str) -> dict:
    url = "http://127.0.0.1:11434/api/generate"
    
    prompt = f"""You are a strict Multilingual Safety Guardrail Agent for an agricultural AI system.
Analyze the following user query for safety, self-harm, poisoning risks, and domain relevance. 

Classify the query as UNSAFE if it contains:
- Intent or questions about humans consuming or tasting pesticides/chemicals.
- Intent of self-harm or suicide using agricultural products.
- Extremely dangerous risks or feeding toxic chemical products to livestock/animals without safety checks.
- Hate speech, political discussions, offensive language, or topics completely unrelated to agriculture, farming, or logistics.

Otherwise, classify it as SAFE.

Provide only the word 'SAFE' or 'UNSAFE' as your output, with no explanation.

User Query: "{user_query}"
Result:"""
    
    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        data = response.json()
        result = data.get('response', '').strip().upper()
        
        if "UNSAFE" in result:
            return {
                "risk_level": "high",
                "reason": "Safety policy violation detected.",
                "escalation_required": True
            }
        
        return {
            "risk_level": "low",
            "reason": "Safe.",
            "escalation_required": False
        }
        
    except Exception:
        return {
            "risk_level": "low",
            "reason": "Safe.",
            "escalation_required": False
        }