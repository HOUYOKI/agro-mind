import requests

def intent_classifier(user_query: str) -> str:
    """
    Classifies the farmer's query to route it to the correct tool or agent.
    """
    url = "http://localhost:11434/api/generate"
    
    prompt = f"""You are an expert intent classifier for the Agro-Mind agricultural project. 
Analyze the following user query and classify it into EXACTLY ONE of these categories:
(Disease_Diagnosis, Logistics_Inquiry, Product_Recommendation, General_Agricultural_Query, Unsafe_Content)

Provide only the category name as your output, with no additional text, explanation, or punctuation.

User Query: "{user_query}"
Classification:"""
    
    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload)
        return response.json()['response'].strip()
    except Exception as e:
        return f"Error: {str(e)}"