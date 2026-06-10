import requests

def classify_intent(user_query: str) -> str:
    url = "http://127.0.0.1:11434/api/generate"
    
    prompt = f"""You are a strict intent classifier for an agricultural AI.
Return ONLY one label from this list: order_status, crop_diagnosis, product_question, pesticide_safety, general_question.
Do not provide any explanation or extra text.

User Query: "{user_query}"
Label:"""
    
    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        data = response.json()
        result = data.get('response', '').strip().lower()
        
        valid_intents = ["order_status", "crop_diagnosis", "product_question", "pesticide_safety", "general_question"]
        
        for intent in valid_intents:
            if intent in result:
                return intent
                
        return "general_question"
    except Exception:
        return "general_question"