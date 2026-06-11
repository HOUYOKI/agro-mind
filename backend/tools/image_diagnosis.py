import requests
import base64
from typing import Dict, Any

URL = "http://localhost:11434/api/generate"


def encode_image(image_path: str) -> str:
    """
    Converts image to base64 string for vision model input.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def analyze_crop_image(image_path: str) -> Dict[str, Any]:
    """
    Uses a vision-capable model (via Ollama or similar) to analyze crop disease images.
    Returns diagnosis, confidence, and explanation.
    """

    image_base64 = encode_image(image_path)

    prompt = f"""
You are an expert agricultural AI (Agro-Mind Vision Agent).

Analyze the following crop image and provide:
1. Most likely disease or pest
2. Confidence level (0-100)
3. Brief explanation of symptoms
4. Recommended next action (non-harmful, safe agricultural advice)

Rules:
- Do NOT give unsafe pesticide dosage instructions
- If uncertain, say "Low confidence - recommend human agronomist review"
- Be conservative and avoid hallucination

Return ONLY valid JSON in this format:
{{
  "disease": "",
  "confidence": 0,
  "explanation": "",
  "recommendation": ""
}}

Image (base64):
{image_base64}
"""

    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(URL, json=payload)
        result_text = response.json()["response"]

        # Try to parse JSON safely
        import json
        return json.loads(result_text)

    except Exception as e:
        return {
    "condition": result.get("disease", ""),
    "confidence": result.get("confidence", 0),
    "symptoms": result.get("explanation", ""),
    "recommendation": result.get("recommendation", "")
}
