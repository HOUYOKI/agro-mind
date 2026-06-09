import requests

def safety_checker(user_query: str) -> bool:
    """
    Checks if the user query is safe and relevant to the agricultural domain.
    Returns True if safe, False if unsafe/harmful.
    """
    url = "http://localhost:11434/api/generate"
    
    prompt = f"""Analyze the following user query for safety and domain relevance. 
If the query contains hate speech, political discussion, offensive language, or is entirely unrelated to agriculture, farming, or logistics, classify it as UNSAFE. 
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
        response = requests.post(url, json=payload)
        result = response.json()['response'].strip().upper()
        return True if "SAFE" in result else False
    except Exception as e:
        print(f"Safety check error: {e}")
        return False