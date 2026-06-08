import base64
from dataclasses import dataclass
from typing import Dict, Any, Optional

# -----------------------------
# Data structure for response
# -----------------------------
@dataclass
class DiagnosisResult:
    disease: str
    confidence: float
    symptoms: list
    recommendation_hint: str
    severity: str


# -----------------------------
# Helper: encode image
# -----------------------------
def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


# -----------------------------
# MAIN TOOL
# -----------------------------
def analyze_crop_image(
    image_path: str,
    use_llm: bool = False,
    client=None
) -> Dict[str, Any]:
    """
    Agro-Mind Image Diagnosis Tool
    Input: image_path
    Output: structured diagnosis
    """

    # -------------------------
    # MODE 1: MOCK (default)
    # -------------------------
    if not use_llm:
        return mock_diagnosis(image_path)

    # -------------------------
    # MODE 2: LLM VISION
    # -------------------------
    if client is None:
        raise ValueError("LLM client must be provided when use_llm=True")

    base64_image = encode_image_to_base64(image_path)

    prompt = """
    You are an expert agricultural crop disease diagnostician.

    Analyze the image and return:
    - disease name
    - confidence (0 to 1)
    - visible symptoms
    - severity (low, medium, high)
    - recommended next steps

    IMPORTANT:
    - Do NOT guess if unclear
    - If uncertain, say "uncertain diagnosis"
    - Focus on crop diseases, pests, nutrient deficiencies
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    )

    result_text = response.choices[0].message.content

    return {
        "raw_output": result_text,
        "mode": "llm"
    }


# -----------------------------
# MOCK DIAGNOSIS (important for MVP)
# -----------------------------
def mock_diagnosis(image_path: str) -> Dict[str, Any]:
    """
    Fake but realistic crop diagnosis output
    used for MVP when no vision model is connected
    """

    # simple heuristic (you can upgrade later)
    filename = image_path.lower()

    if "leaf" in filename:
        result = DiagnosisResult(
            disease="Leaf Blight (possible fungal infection)",
            confidence=0.78,
            symptoms=[
                "yellow/brown spots on leaves",
                "leaf curling",
                "dry patches"
            ],
            recommendation_hint="Use copper-based fungicide and remove infected leaves",
            severity="medium"
        )

    elif "spot" in filename:
        result = DiagnosisResult(
            disease="Bacterial Leaf Spot",
            confidence=0.74,
            symptoms=[
                "dark circular lesions",
                "water-soaked spots"
            ],
            recommendation_hint="Apply antibacterial crop protection spray",
            severity="medium"
        )

    else:
        result = DiagnosisResult(
            disease="Unknown or Mixed Condition",
            confidence=0.55,
            symptoms=["unclear visual symptoms"],
            recommendation_hint="Recommend human agronomist review",
            severity="low"
        )

    return {
        "disease": result.disease,
        "confidence": result.confidence,
        "symptoms": result.symptoms,
        "recommendation_hint": result.recommendation_hint,
        "severity": result.severity,
        "mode": "mock"
    }