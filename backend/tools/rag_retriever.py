import os
import requests
import json

def retrieve_agronomy_knowledge(user_query: str, intent: str = "") -> dict:
    data_path = r"D:\agro-mind\backend\data\cat1_usage_product_real.jsonl"
    
    context = ""
    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                parsed_data = []
                for line in lines:
                    try:
                        entry = json.loads(line)
                        parsed_data.append(str(entry))
                    except:
                        continue
                context = "\n".join(parsed_data[-5:])
        except Exception:
            context = ""

    prompt = f"Data: {context}\n\nUser Query: {user_query}\nAnswer based on data in Arabic. If not found, return NO_DATA."
    
    url = "http://localhost:11434/api/generate"
    payload = {"model": "qwen2.5:7b", "prompt": prompt, "stream": False}
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        data = response.json()
        result = data.get('response', '').strip()
        
        if "NO_DATA" in result or not result:
            return {
                "rag_used": True, 
                "found": False, 
                "summary": "No relevant info found.", 
                "sources": [], 
                "confidence": 0.0,
                "status": "completed"
            }
        
        return {
            "rag_used": True, 
            "found": True, 
            "summary": result, 
            "sources": ["product_database"], 
            "confidence": 0.95,
            "status": "completed"
        }
        
    except Exception:
        return {
            "rag_used": True, 
            "found": False, 
            "summary": "Error reaching AI service.", 
            "sources": [], 
            "confidence": 0.0,
            "status": "failed"
        }