import json
import os
import requests

def lookup_order(user_query: str, customer_id: str) -> dict:
    full_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cat3_aftersales_logistics_real.jsonl')
    
    context = ""
    if os.path.exists(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-15:]
                context = "\n".join([line.strip() for line in lines])
        except Exception:
            context = ""

    url = "http://127.0.0.1:11434/api/generate"
    
    prompt = f"""You are a logistics assistant. 
    Use the following reference context to answer the user query:
    {context}
    
    Analyze the user query: "{user_query}"
    If order information is found, provide status, ETA, and tracking number.
    If no information is found, return 'NOT_FOUND'.
    """
    
    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        ai_response = data.get('response', '').strip()
        
        if "NOT_FOUND" in ai_response or not ai_response:
            return {
                "order_found": False,
                "order_id": None,
                "status": None,
                "eta": None,
                "tracking_number": None,
                "reason": "Order not found in our logs."
            }
        
        return {
            "order_found": True,
            "order_id": "Detected",
            "status": "Found",
            "eta": "Check details",
            "tracking_number": "Check details",
            "reason": ai_response
        }
    except Exception:
        return {
            "order_found": False,
            "order_id": None,
            "status": None,
            "eta": None,
            "tracking_number": None,
            "reason": "System error occurred."
        }