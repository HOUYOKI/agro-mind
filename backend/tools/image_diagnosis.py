import requests
import base64
import json
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
    Uses a vision-capable model through Ollama to analyze crop disease images.
    Returns diagnosis, confidence, explanation, and recommendation.
    """

    image_base64 = encode_image(image_path)

    prompt = f"""
You are an expert agricultural AI called Agro-Mind Vision Agent.

Analyze the following crop image and provide:
1. Most likely disease or pest
2. Confidence level from 0 to 100
3. Brief explanation of visible symptoms
4. Recommended next action using safe agricultural advice

Rules:
- Do NOT give unsafe pesticide dosage instructions.
- If uncertain, say "Low confidence - recommend human agronomist review".
- Be conservative and avoid hallucination.
- Return ONLY valid JSON.

Return the answer in this exact JSON format:
{{
  "disease": "",
  "confidence": 0,
  "explanation": "",
  "recommendation": ""
}}

Image base64:
{image_base64}
"""

    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(URL, json=payload, timeout=60)
        response.raise_for_status()

        result_text = response.json().get("response", "").strip()

        result = json.loads(result_text)

        return {
            "disease": result.get("disease", "Unknown"),
            "confidence": result.get("confidence", 0),
            "explanation": result.get("explanation", ""),
            "recommendation": result.get("recommendation", "Recommend human agronomist review.")
        }

    except Exception as e:
        return {
            "disease": "Unknown",
            "confidence": 0,
            "explanation": "Image analysis failed or returned invalid JSON.",
            "recommendation": "Recommend human agronomist review.",
            "error": str(e)
        }