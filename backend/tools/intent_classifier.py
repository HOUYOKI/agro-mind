import os
import re
import requests

def classify_intent(user_query: str) -> str:
    """
    Advanced Hybrid Intent Classification Engine for Agro-Mind.
    Combines deterministic keyword routing with local LLM (Qwen2.5) intelligence.
    """
    query_clean = user_query.lower().strip()
    
    # 1. Operational Intent Categories
    valid_intents = [
        "crop_diagnosis", 
        "product_question", 
        "pesticide_safety", 
        "order_status",
        "general_question"
    ]

    # 2. Local Ollama Configuration
    url = "http://127.0.0.1:11434/api/generate"
    
    prompt = f"""You are an elite intent classification engine for an agricultural AI system.
Analyze the user query and map it to the single most relevant label from the valid list.

VALID LABELS:
- crop_diagnosis: plant diseases, leaf yellowing, crop symptoms, pests, or plant treatments.
- product_question: specific agricultural products, fertilizers, chemical dosages.
- pesticide_safety: chemical toxicity, safety gear, environmental hazards.
- order_status: shipping, logistics, order tracking.
- general_question: greetings, casual talk, or non-agricultural topics.

CRITICAL: Output ONLY the exact label string. No punctuation, no explanation.

User Query: "{user_query}"
Label:"""
    
    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 10
        }
    }
    
    try:
        # Increased timeout to 60 seconds to accommodate local model loading (Cold Start)
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            raw_output = response.json().get('response', '').strip().lower()
            
            # Professional defensive token parsing using Regex
            extracted_words = re.findall(r'[a-z_]+', raw_output)
            for word in extracted_words:
                if word in valid_intents:
                    return word

    except requests.exceptions.RequestException:
        # If a timeout or connection issue occurs, proceed smoothly to the keyword backup
        pass

    # 3. --- DETERMINISTIC BACKUP ROUTING (Safety Net) ---
    # If LLM times out or misclassifies, catch obvious agricultural terms to trigger RAG
    diagnostic_keywords = ["symptom", "treatment", "yellowing", "disease", "pest", "rot", "leaf", "wilt", "citrus"]
    if any(keyword in query_clean for keyword in diagnostic_keywords):
        return "crop_diagnosis"
        
    return "general_question"