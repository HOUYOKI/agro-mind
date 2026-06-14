import base64
import json
import os
from typing import Dict, Any, Optional

import requests


URL = "http://localhost:11434/api/generate"

# Important:
# qwen2.5:7b is usually text-only.
# For real image analysis, use a vision model such as llava or qwen2.5vl if installed.
VISION_MODEL = "qwen2.5vl:7b"


def encode_image(image_path: str) -> str:
    """
    Converts image to base64 string for vision model input.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _fallback_diagnosis(image_path: str) -> Dict[str, Any]:
    """
    Safe MVP fallback when a real vision model is unavailable.
    Uses filename hints only, so it avoids fake confidence.
    """
    filename = os.path.basename(image_path).lower()

    if "yellow" in filename or "chlorosis" in filename:
        return {
            "disease": "Possible nutrient deficiency or leaf chlorosis",
            "confidence": 0.45,
            "severity": "medium",
            "symptoms": [
                "yellowing leaves",
                "possible nutrient stress",
                "visual diagnosis requires review"
            ],
            "recommendation_hint": "Check watering, soil nutrients, and consult an agronomist before applying treatments.",
            "mode": "fallback"
        }

    if "spot" in filename or "blight" in filename:
        return {
            "disease": "Possible leaf spot or blight",
            "confidence": 0.45,
            "severity": "medium",
            "symptoms": [
                "possible dark or damaged leaf areas",
                "possible fungal or bacterial symptoms",
                "visual diagnosis requires review"
            ],
            "recommendation_hint": "Isolate affected leaves if needed and request agronomist review before pesticide use.",
            "mode": "fallback"
        }

    return {
        "disease": "Unknown or mixed condition",
        "confidence": 0.25,
        "severity": "low",
        "symptoms": [
            "unclear visual symptoms",
            "image requires human agronomist review"
        ],
        "recommendation_hint": "Low confidence. Recommend human agronomist review before treatment.",
        "mode": "fallback"
    }


def _normalize_result(result: Dict[str, Any], mode: str = "llm") -> Dict[str, Any]:
    """
    Normalizes any model response into the format expected by the frontend/backend.
    """
    confidence = result.get("confidence", 0)

    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0

    # If model returns 0-100, convert to 0-1
    if confidence > 1:
        confidence = confidence / 100

    symptoms = result.get("symptoms")

    if symptoms is None:
        explanation = result.get("explanation", "")
        symptoms = [explanation] if explanation else ["No clear symptoms provided."]

    if isinstance(symptoms, str):
        symptoms = [symptoms]

    return {
        "disease": result.get("disease", "Unknown or mixed condition"),
        "confidence": round(confidence, 2),
        "severity": result.get("severity", "unknown"),
        "symptoms": symptoms,
        "recommendation_hint": result.get(
            "recommendation_hint",
            result.get("recommendation", "Recommend human agronomist review.")
        ),
        "mode": mode
    }


def analyze_crop_image(
    image_path: str,
    use_llm: bool = False,
    client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Agro-Mind image diagnosis tool.

    Works safely in two modes:
    - use_llm=False: returns MVP-safe fallback output.
    - use_llm=True: tries local Ollama vision model, then falls back if unavailable.

    Returns:
    disease, confidence, severity, symptoms, recommendation_hint, mode
    """

    if not use_llm:
        return _fallback_diagnosis(image_path)

    try:
        image_base64 = encode_image(image_path)

        prompt = """
You are Agro-Mind Vision Agent, an agricultural image diagnosis assistant.

Analyze the crop image and return ONLY valid JSON in this exact format:

{
  "disease": "",
  "confidence": 0.0,
  "severity": "low/medium/high",
  "symptoms": [],
  "recommendation_hint": ""
}

Rules:
- Be conservative.
- Do not invent a diagnosis if the image is unclear.
- Do not give unsafe pesticide dosage instructions.
- If uncertain, recommend human agronomist review.
"""

        payload = {
            "model": VISION_MODEL,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False
        }

        response = requests.post(URL, json=payload, timeout=90)
        response.raise_for_status()

        result_text = response.json().get("response", "").strip()
        result = json.loads(result_text)

        return _normalize_result(result, mode="llm")

    except Exception as error:
        fallback = _fallback_diagnosis(image_path)
        fallback["error"] = str(error)
        return fallback