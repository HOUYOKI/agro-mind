
import json
import requests

def summarize_conversation(conversation: str) -> dict:
    """
    Agro-Mind Conversation Summarizer

    Purpose:
    - Summarize farmer conversations into structured insights
    - Store results in Agro-Mind memory system
    - Support analytics and follow-up generation
    """

    url = "http://127.0.0.1:11434/api/generate"

    prompt = f"""
You are Agro-Mind, an agricultural AI assistant.
Your ONLY task is to summarize conversations between farmers and the Agro-Mind system.
You must return ONLY valid JSON.
No explanations. No markdown.
Conversation:
\"\"\"{conversation}\"\"\"

Extract:
- summary: short summary of the conversation
- intents: list of user intents (e.g. diagnosis, support, purchase)
- crop_or_disease: main crop or disease mentioned (if any)
- products: any agricultural products mentioned (fertilizers, pesticides, seeds, tools)
- issue_type: pest | disease | irrigation | soil | weather | logistics | other
- escalation_needed: true or false
- resolution_status: resolved | unresolved | partial
- follow_up_actions: list of next recommended actions
Return ONLY this JSON format:

{{
  "summary": "",
  "intents": [],
  "crop_or_disease": "",
  "products": [],
  "issue_type": "",
  "escalation_needed": false,
  "resolution_status": "",
  "follow_up_actions": [],
  "customer_profile_updates": {{
    "crop_type": "",
    "region": "",
    "notes": ""
  }}
}}
"""

    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        result_text = response.json().get("response", "").strip()
        
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        return json.loads(result_text)
    except json.JSONDecodeError:
        return {
            "error": "Model returned invalid JSON",
            "raw_output": result_text
        }
    except Exception as e:
        return {
            "error": str(e)
        }

if __name__ == '__main__':
    print("\n==================================================")
    print("   Running conversation summarizer check...")
    print("==================================================")
    
    sample_conversation = """
    Farmer: I have an orange farm and the leaves are turning yellow. I need a good fertilizer.
    Agro-Mind: It could be a nitrogen deficiency. I recommend applying a balanced citrus fertilizer.
    Farmer: Okay, I will try to buy one tomorrow. Thank you.
    """
    
    print("Sending conversation to qwen2.5:7b...")
    output = summarize_conversation(sample_conversation)
    
    print("\nOutput result:")
    print(json.dumps(output, indent=2, ensure_ascii=False))
    print("==================================================\n")