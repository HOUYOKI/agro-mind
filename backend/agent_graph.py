import re
from typing import TypedDict, Dict, Any, List, Optional

from langgraph.graph import StateGraph, END

from backend.tools.intent_classifier import classify_intent
from backend.tools.safety_checker import check_safety
from backend.tools.product_recommender import recommend_product
from backend.tools.logistics_lookup import lookup_order
from backend.tools.case_memory import save_case
from backend.tools.llm_agent import ask_agro_mind
from backend.tools.rag_retriever import retrieve_agronomy_knowledge
from backend.vision.diagnosis_tool import diagnose_crop_image
from backend.tools.customer_profile import (
    get_customer_profile,
    update_customer_profile,
    summarize_customer_profile,
)


INJECTION_OVERRIDE_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore the above",
    "disregard your rules",
    "disregard previous",
    "forget your instructions",
    "you are now",
    "debug mode",
    "developer mode",
    "print your system prompt",
    "print your instructions",
    "show your instructions",
    "reveal your instructions",
]

_INJECTION_SAFE_RESPONSE = (
    "I can help with agricultural questions — "
    "could you tell me more about the issue you're experiencing?"
)

_OUTPUT_INJECTION_MARKERS = [
    "injection_success",
    "debug mode",
    "developer instructions",
    "system prompt",
]

# ---------------------------------------------------------------------------
# Agricultural signal filter
# ---------------------------------------------------------------------------

AGRICULTURE_KEYWORDS = [
    "crop", "plant", "leaf", "leaves", "fruit", "vegetable", "soil",
    "tomato", "cucumber", "citrus", "grape", "potato", "pepper", "wheat", "corn",
    "yellow", "yellowing", "spots", "spot", "rot", "rotting", "mold", "mildew",
    "blight", "rust", "aphid", "whitefly", "pest", "disease", "fungus",
    "spray", "pesticide", "fungicide", "fertilizer", "product",

    # Chinese agriculture terms
    "\u4f5c\u7269", "\u690d\u7269", "\u53f6", "\u53f6\u7247", "\u679c\u5b9e", "\u852c\u83dc", "\u571f\u58e4",
    "\u756a\u8304", "\u9ec4\u74dc", "\u67d1\u6a58", "\u8461\u8404", "\u571f\u8c46", "\u8fa3\u6912", "\u5c0f\u9ea6", "\u7389\u7c73",
    "\u53d1\u9ec4", "\u658d\u70b9", "\u8150\u70c2", "\u9727", "\u75c5\u5bb3", "\u5bb3\u866b", "\u771f\u83cc",
    "\u519c\u836f", "\u6740\u83cc\u5242", "\u5316\u80a5", "\u55b7\u6d12",
]

SUSPICIOUS_NON_AGRI_PATTERNS = [
    "customer record",
    "internal record",
    "database",
    "query formatting",
    "suspicious query",
    "debug",
    "system prompt",
    "hidden rules",
]

# Known non-fruit / non-plant brand/model names that users might accidentally use
KNOWN_NON_PLANT_NOUNS = [
    "toyota", "camry", "honda", "ford", "bmw", "mercedes", "iphone", "samsung",
    "laptop", "computer", "phone", "car", "truck", "vehicle", "airplane",
]


def has_agricultural_signal(message: str) -> bool:
    """Return True only if the message contains clear agricultural content."""
    text = (message or "").lower()

    if any(pattern in text for pattern in SUSPICIOUS_NON_AGRI_PATTERNS):
        return False

    tokens = re.findall(r"[A-Za-z0-9\u4E00-\u9FFF]+", text)
    if len(tokens) < 3:
        return False

    return any(keyword in text for keyword in AGRICULTURE_KEYWORDS)


def message_mentions_real_plant(message: str) -> bool:
    """
    Extra guard: if the message contains a known non-plant noun alongside 'fruit',
    we know the crop name is fictitious.
    """
    text = (message or "").lower()
    return any(noun in text for noun in KNOWN_NON_PLANT_NOUNS)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgroState(TypedDict, total=False):
    customer_id: str
    message: str

    image_path: Optional[str]
    image_filename: Optional[str]
    image_result: Dict[str, Any]
    message_for_tools: str

    raw_intent: str
    intent: str
    safety_result: Dict[str, Any]

    customer_profile: Optional[Dict[str, Any]]
    customer_profile_summary: str

    product_result: Dict[str, Any]
    order_result: Dict[str, Any]
    rag_result: Dict[str, Any]

    response_text: str
    ai_response: str
    llm_status: str

    saved_case: Dict[str, Any]
    updated_customer_profile: Dict[str, Any]

    execution_trace: List[Dict[str, Any]]


# ==========================================
# DEFAULT TOOL OUTPUTS
# ==========================================

def default_product_result() -> Dict[str, Any]:
    return {
        "recommended_product": None,
        "product_id": None,
        "confidence": 0.0,
        "reason": "Product recommendation not needed for this intent.",
        "safety_note": None,
        "detected_crop": None,
        "detected_issue": None,
    }


def default_order_result() -> Dict[str, Any]:
    return {
        "order_found": False,
        "order_id": None,
        "status": None,
        "eta": None,
        "tracking_number": None,
        "reason": "Order lookup not needed for this intent.",
    }


def default_rag_result() -> Dict[str, Any]:
    return {
        "rag_used": False,
        "found": False,
        "summary": "RAG retrieval not needed for this intent.",
        "sources": [],
        "confidence": 0.0,
        "status": "skipped",
    }


def default_image_result() -> Dict[str, Any]:
    return {
        "image_uploaded": False,
        "status": "skipped",
        "success": None,
        "vision_used": False,

        "crop": None,
        "detected_crop": None,
        "plant": None,
        "disease": None,
        "possible_disease": None,
        "predicted_class": None,

        # Can be nested dict from diagnosis_tool.py
        "diagnosis": None,

        "confidence": 0.0,
        "score": None,
        "severity": None,
        "symptoms": None,
        "visual_symptoms": None,

        "recommendation_hint": None,
        "recommendation": None,
        "safe_response": None,
        "response": None,

        "best_product": None,
        "recommended_products": [],
        "debug_best_product": None,
        "debug_recommended_products": [],

        "human_review_required": False,
        "needs_human_review": False,
        "escalation_required": False,

        "reason": "Image diagnosis not used.",
    }


def add_trace(
    state: AgroState,
    step: int,
    task: str,
    status: str,
    result: Any = None,
) -> AgroState:
    trace = state.get("execution_trace", [])
    trace.append({"step": step, "task": task, "status": status, "result": result})
    state["execution_trace"] = trace
    return state


def normalize_intent(raw_intent: str) -> str:
    value = (raw_intent or "").strip().lower()
    mapping = {
        "crop": "crop_diagnosis",
        "diagnosis": "crop_diagnosis",
        "crop_problem": "crop_diagnosis",
        "crop_diagnosis": "crop_diagnosis",
        "vision": "crop_diagnosis",
        "vision_analysis": "crop_diagnosis",
        "image": "crop_diagnosis",
        "image_diagnosis": "crop_diagnosis",

        "product": "product_question",
        "product_recommendation": "product_question",
        "product_information": "product_question",
        "product_question": "product_question",

        "pesticide": "pesticide_safety",
        "safety": "pesticide_safety",
        "pesticide_safety": "pesticide_safety",

        "order": "order_status",
        "order_lookup": "order_status",
        "order_status": "order_status",

        "complaint": "complaint",
        "complaints": "complaint",

        "agriculture_knowledge": "general_question",
        "customer_profile": "general_question",
        "general": "general_question",
        "general_question": "general_question",
    }
    return mapping.get(value, "general_question")


# ==========================================
# IMAGE HELPERS
# ==========================================

_IMAGE_LABEL_TRANSLATIONS = {
    "玫瑰": "rose",
    "月季": "rose",
    "黑斑病": "black spot disease",
    "苹果": "apple",
    "苹果树": "apple tree",
    "轮纹病": "ring rot disease",
    "番茄": "tomato",
    "早疫病": "early blight",
    "柑橘": "citrus",
    "疮痂病": "scab disease",
    "炭疽病": "anthracnose",
    "白粉病": "powdery mildew",
    "霜霉病": "downy mildew",
    "灰霉病": "gray mold",
    "根腐": "root rot",
    "根腐病": "root rot",
    "叶斑病": "leaf spot disease",
    "软腐病": "soft rot",
    "溃疡病": "canker disease",
    "真菌病害": "fungal disease",
    "细菌病害": "bacterial disease",
    "虫害": "pest damage",
    "锈病": "rust disease",
}


def _translate_image_label(value):
    if value is None:
        return None

    if isinstance(value, str):
        return _IMAGE_LABEL_TRANSLATIONS.get(value, value)

    if isinstance(value, list):
        return [_translate_image_label(item) for item in value]

    return value


def _image_value(image_result: Dict[str, Any], *keys):
    """
    Read a value from a dictionary.

    Important:
    Skip nested dictionaries. diagnosis_tool.py returns image_result["diagnosis"]
    as a dictionary, so returning that as a disease string is wrong.
    """
    if not isinstance(image_result, dict):
        return None

    for key in keys:
        value = image_result.get(key)

        if value in [None, "", [], {}]:
            continue

        if isinstance(value, dict):
            continue

        return value

    return None


def _image_diagnosis_dict(image_result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(image_result, dict):
        return {}

    diagnosis = image_result.get("diagnosis")
    return diagnosis if isinstance(diagnosis, dict) else {}


def _image_value_nested(image_result: Dict[str, Any], *keys):
    """
    Check top-level image_result first, then nested image_result["diagnosis"].

    This fixes the issue where diagnosis_tool.py returns:
        {
          "diagnosis": {
             "crop": "...",
             "disease": "...",
             "confidence": ...
          }
        }
    """
    value = _image_value(image_result, *keys)

    if value not in [None, "", [], {}]:
        return value

    diagnosis = _image_diagnosis_dict(image_result)
    return _image_value(diagnosis, *keys)


def _image_crop(image_result: Dict[str, Any]):
    return _translate_image_label(
        _image_value_nested(
            image_result,
            "crop",
            "detected_crop",
            "plant",
        )
    )


def _image_issue(image_result: Dict[str, Any]):
    return _translate_image_label(
        _image_value_nested(
            image_result,
            "disease",
            "possible_disease",
            "predicted_class",
            "disease_type",
            "issue",
        )
    )


def _image_confidence(image_result: Dict[str, Any]):
    return _image_value_nested(
        image_result,
        "confidence",
        "score",
        "similarity",
    )


def _image_symptoms(image_result: Dict[str, Any]):
    return _translate_image_label(
        _image_value_nested(
            image_result,
            "symptoms",
            "visual_symptoms",
        )
    )


def _image_safe_response(image_result: Dict[str, Any]):
    return _image_value(
        image_result,
        "response",
        "safe_response",
        "customer_response",
        "recommendation_hint",
        "recommendation",
    )


def _image_needs_review(image_result: Dict[str, Any]) -> bool:
    if not isinstance(image_result, dict):
        return False

    diagnosis = _image_diagnosis_dict(image_result)

    return bool(
        image_result.get("needs_human_review")
        or image_result.get("human_review_required")
        or image_result.get("escalation_required")
        or diagnosis.get("needs_human_review")
        or diagnosis.get("human_review_required")
        or diagnosis.get("escalation_required")
    )


def _force_language_from_customer_message(message: str) -> str:
    """
    Response language must be based on the raw user message only.

    Image-only upload means message is empty, so default to English.
    Do not infer Chinese from image/RAG/tool data.
    """
    if re.search(r"[\u4E00-\u9FFF]", message or ""):
        return "Chinese"

    return "English"


def build_message_for_tools(message: str, image_result: Dict[str, Any]) -> str:
    """
    Converts the structured image diagnosis into text that the product recommender
    and RAG retriever can understand.

    This is important for image-only cases where the user uploads a photo and writes
    little or no text.
    """
    if not image_result.get("image_uploaded"):
        return message or ""

    crop = _image_crop(image_result)
    disease = _image_issue(image_result)
    symptoms = _image_symptoms(image_result)
    confidence = _image_confidence(image_result)

    image_context = (
        "Uploaded crop image analysis. "
        f"Detected crop: {crop}. "
        f"Possible disease or issue: {disease}. "
        f"Visible symptoms: {symptoms}. "
        f"Image confidence: {confidence}. "
    )

    if message:
        return f"{message}\n\n{image_context}"

    return image_context


# ==========================================
# GRAPH NODES
# ==========================================

def load_customer_profile_node(state: AgroState) -> AgroState:
    customer_id = state["customer_id"]
    profile = get_customer_profile(customer_id)
    summary = summarize_customer_profile(customer_id)
    state["customer_profile"] = profile
    state["customer_profile_summary"] = summary
    return add_trace(
        state,
        step=1,
        task="Load customer profile",
        status="completed" if profile else "not_found",
        result=profile.get("profile_summary") if profile else "No existing customer profile found",
    )


def image_diagnosis_node(state: AgroState) -> AgroState:
    """
    This makes image diagnosis an internal agent tool.

    The user no longer has to use a separate /diagnose path.
    /chat can receive an optional image, then this node runs the vision diagnosis.
    """
    image_path = state.get("image_path")

    if not image_path:
        state["image_result"] = default_image_result()
        state["message_for_tools"] = state.get("message", "")
        return add_trace(
            state,
            step=2,
            task="Run image diagnosis if image uploaded",
            status="skipped",
            result="No image uploaded",
        )

    try:
        result = diagnose_crop_image(
            image_path=image_path,
            user_text=state.get("message", ""),
        ) or {}

        result["image_uploaded"] = True
        result["status"] = result.get("status", "completed")

        state["image_result"] = result
        state["message_for_tools"] = build_message_for_tools(
            state.get("message", ""),
            result,
        )

        return add_trace(
            state,
            step=2,
            task="Run image diagnosis if image uploaded",
            status="completed",
            result={
                "crop": _image_crop(result),
                "disease": _image_issue(result),
                "confidence": _image_confidence(result),
                "human_review_required": _image_needs_review(result),
            },
        )

    except Exception as error:
        result = default_image_result()
        result.update(
            {
                "image_uploaded": True,
                "status": "error",
                "reason": f"Image diagnosis failed: {str(error)}",
                "human_review_required": True,
                "escalation_required": True,
            }
        )

        state["image_result"] = result
        state["message_for_tools"] = state.get("message", "")

        return add_trace(
            state,
            step=2,
            task="Run image diagnosis if image uploaded",
            status="error",
            result=str(error),
        )


def classify_intent_node(state: AgroState) -> AgroState:
    message = state.get("message", "")
    image_result = state.get("image_result", default_image_result())

    raw_intent = classify_intent(message)
    intent = normalize_intent(raw_intent)

    # If an image exists, treat it as crop diagnosis unless the user text is clearly
    # safety, order, or complaint.
    if image_result.get("image_uploaded") and intent in [
        "general_question",
        "crop_diagnosis",
        "product_question",
    ]:
        raw_intent = "vision_analysis"
        intent = "crop_diagnosis"

    state["raw_intent"] = raw_intent
    state["intent"] = intent

    return add_trace(
        state,
        step=3,
        task="Classify customer intent",
        status="completed",
        result=intent,
    )


def safety_check_node(state: AgroState) -> AgroState:
    safety_result = check_safety(state["message"], state["intent"])
    image_result = state.get("image_result", default_image_result())

    # If vision says the image needs human review, raise it to a medium escalation
    # unless the text safety checker already marked it high.
    if image_result.get("image_uploaded") and _image_needs_review(image_result):
        if safety_result.get("risk_level") == "low":
            safety_result = {
                "risk_level": "medium",
                "reason": "Image diagnosis requires human agronomist review.",
                "escalation_required": True,
            }

    state["safety_result"] = safety_result

    return add_trace(
        state,
        step=4,
        task="Check safety risk",
        status="completed",
        result=safety_result.get("risk_level"),
    )


def init_defaults_node(state: AgroState) -> AgroState:
    state["product_result"] = default_product_result()
    state["order_result"] = default_order_result()
    state["rag_result"] = default_rag_result()
    return state


def product_and_rag_node(state: AgroState) -> AgroState:
    intent = state["intent"]
    safety_result = state["safety_result"]

    # Use image-enriched text when available.
    message = state.get("message_for_tools") or state["message"]

    # FIX 1: Block RAG + product if message has no real agricultural signal.
    # FIX 2: Block product if message mentions a known non-plant noun.
    if intent in ["crop_diagnosis", "product_question"] and (
        not has_agricultural_signal(message) or message_mentions_real_plant(message)
    ):
        state["product_result"] = default_product_result()
        state["product_result"]["reason"] = (
            "Message does not contain a valid agricultural crop or issue. "
            "Product recommendation skipped."
        )
        state["rag_result"] = default_rag_result()
        state["rag_result"]["summary"] = (
            "Message does not contain a valid agricultural crop or issue. "
            "RAG retrieval skipped."
        )
        state = add_trace(
            state,
            step=5,
            task="Retrieve agronomy knowledge if needed",
            status="skipped",
            result="Skipped — message is not clearly agricultural or contains a non-plant noun",
        )
        state = add_trace(
            state,
            step=6,
            task="Run product recommendation if needed",
            status="skipped",
            result="Skipped — message is not clearly agricultural or contains a non-plant noun",
        )
        return state

    if (
        intent in ["crop_diagnosis", "product_question"]
        and not safety_result.get("escalation_required", False)
    ):
        try:
            product_result = recommend_product(message)
            if product_result:
                state["product_result"].update(product_result)
        except Exception as error:
            state["product_result"] = default_product_result()
            state["product_result"]["reason"] = f"Product recommendation failed: {str(error)}"

    # Only crop/product intents use RAG.
    if (
        intent in ["crop_diagnosis", "product_question"]
        and not safety_result.get("escalation_required", False)
    ):
        try:
            rag_result = retrieve_agronomy_knowledge(message, intent)
            if rag_result:
                state["rag_result"].update(rag_result)
        except Exception as error:
            state["rag_result"] = default_rag_result()
            state["rag_result"]["summary"] = f"RAG retrieval failed: {str(error)}"
            state["rag_result"]["status"] = "error"

    state = add_trace(
        state,
        step=5,
        task="Retrieve agronomy knowledge if needed",
        status="completed" if state["rag_result"].get("rag_used") else "skipped",
        result=(
            state["rag_result"].get("summary")
            if state["rag_result"].get("found")
            else "No RAG knowledge found"
        ),
    )
    state = add_trace(
        state,
        step=6,
        task="Run product recommendation if needed",
        status=(
            "completed"
            if intent in ["crop_diagnosis", "product_question"]
            and not safety_result.get("escalation_required", False)
            else "skipped"
        ),
        result=state["product_result"].get("recommended_product"),
    )
    return state


def order_lookup_node(state: AgroState) -> AgroState:
    try:
        order_result = lookup_order(state["message"], state["customer_id"])
        if order_result:
            state["order_result"].update(order_result)
    except Exception as error:
        state["order_result"] = default_order_result()
        state["order_result"]["reason"] = f"Order lookup failed: {str(error)}"
    return add_trace(
        state,
        step=5,
        task="Run order lookup if needed",
        status="completed",
        result=state["order_result"].get("status"),
    )


def escalation_node(state: AgroState) -> AgroState:
    state["rag_result"] = default_rag_result()
    state["product_result"] = default_product_result()
    state["order_result"] = default_order_result()

    risk_level = state["safety_result"].get("risk_level")
    intent = state["intent"]
    image_result = state.get("image_result", default_image_result())

    if risk_level == "high":
        state["product_result"]["reason"] = "High-risk safety case. Product recommendation disabled."
    elif intent == "complaint":
        state["product_result"]["reason"] = "Complaint or damage claim requires human review. Product recommendation disabled."
    elif image_result.get("image_uploaded") and _image_needs_review(image_result):
        state["product_result"]["reason"] = "Image diagnosis requires human review. Product recommendation disabled."
    else:
        state["product_result"]["reason"] = "Product recommendation not needed for this intent."

    state = add_trace(
        state,
        step=5,
        task="Retrieve agronomy knowledge if needed",
        status="skipped",
        result="Skipped due to safety or escalation risk",
    )
    state = add_trace(
        state,
        step=6,
        task="Run product recommendation if needed",
        status="skipped",
        result=None,
    )
    return state


def general_node(state: AgroState) -> AgroState:
    state["rag_result"] = default_rag_result()
    state["product_result"] = default_product_result()
    return add_trace(
        state,
        step=5,
        task="Handle general question",
        status="completed",
        result="General response path — RAG and product recommendation skipped",
    )


def build_rule_based_response(state: AgroState) -> str:
    intent = state["intent"]
    safety_result = state["safety_result"]
    product_result = state["product_result"]
    order_result = state["order_result"]
    image_result = state.get("image_result", default_image_result())

    if safety_result.get("risk_level") == "high":
        return (
            "This may involve poison ingestion, chemical exposure, or self-harm risk. "
            "Do not consume or touch the substance. Contact local emergency services, "
            "poison control, or a medical professional immediately. If this involves a pesticide, "
            "keep the product label available for the professional to review. "
            "This case has been flagged for human review."
        )

    if intent == "pesticide_safety":
        return (
            "I cannot confirm whether the crop is safe to eat from the message alone. "
            "Please check the exact product label for the required pre-harvest interval "
            "and safety instructions. A human agricultural expert should review this case."
        )

    if intent == "complaint":
        return (
            "I'm sorry this happened. Because this involves a complaint or possible crop damage, "
            "a human support expert should review the case before any final decision is made."
        )

    if intent == "order_status":
        if order_result.get("order_found"):
            return (
                f"Your order {order_result.get('order_id')} is currently "
                f"{order_result.get('status')}. "
                f"Estimated arrival: {order_result.get('eta')}. "
                f"Tracking number: {order_result.get('tracking_number')}."
            )
        return order_result.get("reason") or "I could not find this order."

    if image_result.get("image_uploaded"):
        safe_image_response = _image_safe_response(image_result)
        if safe_image_response:
            return safe_image_response

        image_issue = _image_issue(image_result)
        image_crop = _image_crop(image_result)
        image_confidence = _image_confidence(image_result)

        if image_issue:
            crop_phrase = f" on {image_crop}" if image_crop else ""
            return (
                f"The uploaded image may show {image_issue}{crop_phrase}. "
                f"Confidence: {image_confidence}. "
                "Please treat this as a possible diagnosis, not a final confirmation. "
                "A human agronomist should confirm the issue before pesticide or treatment decisions."
            )

    if product_result.get("recommended_product"):
        return (
            f"{product_result.get('recommended_product')} may be relevant based on the available information. "
            "Please confirm the crop issue before applying any product, and follow the official label instructions."
        )

    return (
        "I can help, but I do not have enough reliable information to make a specific recommendation. "
        "Please share the crop, symptoms, and when the issue started."
    )


def generate_response_node(state: AgroState) -> AgroState:
    product_result = state["product_result"]
    order_result = state["order_result"]
    rag_result = state["rag_result"]
    safety_result = state["safety_result"]
    image_result = state.get("image_result", default_image_result())

    fallback_response = build_rule_based_response(state)
    state["response_text"] = fallback_response

    message = state["message"]

    if any(pattern in message.lower() for pattern in INJECTION_OVERRIDE_PATTERNS):
        print("INJECTION PRE-FILTER: blocked message matching override pattern")
        state["ai_response"] = _INJECTION_SAFE_RESPONSE
        state["llm_status"] = "blocked_injection_pattern"
        return add_trace(
            state,
            step=7,
            task="Generate final response with Qwen",
            status="blocked_injection_pattern",
            result="Injection override pattern detected — LLM call skipped",
        )

    response_language = _force_language_from_customer_message(message)

    final_prompt = f"""
You are writing the final customer-facing chatbot response for Agro-Mind, an agricultural support platform.

Customer current message:
[CUSTOMER_MESSAGE_START]
{message}
[CUSTOMER_MESSAGE_END]

Customer profile context:
[CUSTOMER_PROFILE_START]
{state.get("customer_profile_summary", "No customer profile found.")}
[CUSTOMER_PROFILE_END]

Tool results:

Intent classifier:
- Raw intent: {state.get("raw_intent")}
- Normalized intent: {state.get("intent")}

Safety checker:
- Risk level: {safety_result.get("risk_level")}
- Safety reason: {safety_result.get("reason")}
- Escalation required: {safety_result.get("escalation_required")}

Image diagnosis:
- Image uploaded: {image_result.get("image_uploaded")}
- Status: {image_result.get("status")}
- Crop: {_image_crop(image_result)}
- Disease/diagnosis: {_image_issue(image_result)}
- Confidence: {_image_confidence(image_result)}
- Severity: {_image_value_nested(image_result, "severity")}
- Symptoms: {_image_symptoms(image_result)}
- Safe image response: {_image_safe_response(image_result)}
- Image review required: {_image_needs_review(image_result)}
- Image reason: {image_result.get("reason") or image_result.get("message")}

Product recommender:
- Detected crop: {product_result.get("detected_crop")}
- Detected issue: {product_result.get("detected_issue")}
- Recommended product: {product_result.get("recommended_product")}
- Product ID: {product_result.get("product_id")}
- Product confidence: {product_result.get("confidence")}
- Product reason: {product_result.get("reason")}
- Safety note: {product_result.get("safety_note")}

RAG retriever:
- RAG used: {rag_result.get("rag_used")}
- Knowledge found: {rag_result.get("found")}
- Knowledge summary: {rag_result.get("summary")}
- Sources: {rag_result.get("sources")}
- Confidence: {rag_result.get("confidence")}
- RAG status: {rag_result.get("status")}

Order lookup:
- Order found: {order_result.get("order_found")}
- Order ID: {order_result.get("order_id")}
- Status: {order_result.get("status")}
- ETA: {order_result.get("eta")}
- Tracking number: {order_result.get("tracking_number")}
- Order reason: {order_result.get("reason")}

Write the final answer.

LANGUAGE RULE:
This system supports English and Chinese ONLY.
The selected response language is: {response_language}.
Respond ONLY in the selected response language.
If the customer message is empty because the user uploaded only an image, respond in English.
Tool results may contain Chinese crop names, disease names, product names, or source text. Do NOT switch to Chinese because of tool results.
If the selected response language is English, translate or paraphrase any Chinese tool labels into English when possible.
Do not mention this language rule to the customer.

CONTENT RULES:
1. Do not greet with "Dear", "Hello C001", or write like an email.
2. Do not end with "Best regards" or "Agro-Mind Team".
3. Do not mention internal words like "intent", "tool result", "risk_level", "RAG", "debug", "customer_segment", or "upsell_opportunity".
4. Do not invent anything not shown in the tool results.
5. If no exact product match exists, say that clearly.
6. If the recommended product is only a general support product, do not present it as a guaranteed solution.
7. If escalation_required is True, say that a human expert should review or confirm the case.
8. For pesticide, chemical, harvest, dosage, or food safety, never give exact waiting periods, dosage numbers, dilution ratios, application intervals, number of applications, or safety guarantees.
9. If the customer asks whether food can be eaten after spraying, say you cannot confirm safety from the message alone. Tell them to check the specific product label for the pre-harvest interval or waiting period and consult a human agricultural expert.
10. If retrieved knowledge is found, use it to support the answer, but do not pretend it is a final diagnosis.
11. Keep the answer between 3 and 6 short sentences.
12. Sound like a helpful chatbot, not a formal email.
13. Avoid saying a product "will effectively control," "can effectively manage," or guarantees treatment. Use cautious wording like "may help," "could be relevant," or "may support management," and recommend confirming the diagnosis first.
14. CRITICAL — HALLUCINATION GUARD: If detected_crop is None and no image crop was found, do NOT recommend any product. Instead, ask the customer to clarify which crop or plant they are referring to.
15. CRITICAL — HALLUCINATION GUARD: If recommended_product is None, do NOT suggest any product name. Only say no exact product match was found if the customer asked for a product.
16. If an image was uploaded, use the image diagnosis as supporting evidence, not as a guaranteed final diagnosis.
17. Mention low confidence or human review when Image review required is True.
18. If the customer uploaded an image but gave little text, still answer based on the image diagnosis result and ask for crop/symptom confirmation.
19. If Safe image response is available and relevant, you may use it as the main basis of the answer, but keep the selected response language.
"""

    try:
        llm_response = ask_agro_mind(
            final_prompt,
            original_user_message=message,
            force_language=response_language,
        )

        if any(marker in llm_response.lower() for marker in _OUTPUT_INJECTION_MARKERS):
            print("INJECTION OUTPUT-FILTER: discarding LLM response containing injection marker")
            state["ai_response"] = _INJECTION_SAFE_RESPONSE
            state["llm_status"] = "blocked_injection_output"
        else:
            state["ai_response"] = llm_response
            state["llm_status"] = "success"
    except Exception as error:
        print(f"LLM error: {error}")
        state["ai_response"] = fallback_response
        state["llm_status"] = "failed_fallback_used"

    return add_trace(
        state,
        step=7,
        task="Generate final response with Qwen",
        status=state["llm_status"],
        result={
            "success": "Final chatbot response generated",
            "blocked_injection_output": "LLM output contained injection marker — safe response used",
        }.get(state["llm_status"], "Fallback rule-based response used"),
    )


def _to_csv(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v is not None) or None
    return value


def save_case_node(state: AgroState) -> AgroState:
    image_result = state.get("image_result", default_image_result())

    detected_issue = (
        state["product_result"].get("detected_issue")
        or _image_issue(image_result)
    )

    saved_case = save_case(
        customer_id=state["customer_id"],
        message=state["message"],
        intent=state["intent"],
        possible_issue=_to_csv(detected_issue),
        recommended_product=state["product_result"].get("recommended_product"),
        risk_level=state["safety_result"].get("risk_level", "low"),
        escalation_required=state["safety_result"].get("escalation_required", False),
        order_id=state["order_result"].get("order_id"),
        order_status=state["order_result"].get("status"),
    )
    state["saved_case"] = saved_case
    return add_trace(
        state,
        step=8,
        task="Save support case",
        status="completed" if saved_case.get("case_saved") else "skipped",
        result=saved_case.get("reason"),
    )


def update_customer_profile_node(state: AgroState) -> AgroState:
    image_result = state.get("image_result", default_image_result())

    crop = (
        state["product_result"].get("detected_crop")
        or _image_crop(image_result)
    )

    possible_issue = (
        state["product_result"].get("detected_issue")
        or _image_issue(image_result)
    )

    updated_profile = update_customer_profile(
        state["customer_id"],
        {
            "last_intent": state["intent"],
            "last_message": state["message"],
            "crop": crop,
            "possible_issue": possible_issue,
            "recommended_product": state["product_result"].get("recommended_product"),
            "risk_level": state["safety_result"].get("risk_level"),
            "order_id": state["order_result"].get("order_id"),
            "order_status": state["order_result"].get("status"),
            "human_escalation_requested": state["safety_result"].get("escalation_required", False),
            "escalation_required": state["safety_result"].get("escalation_required", False),
            "last_image_uploaded": image_result.get("image_uploaded", False),
            "last_image_diagnosis": _image_issue(image_result),
        },
    )
    state["updated_customer_profile"] = updated_profile
    return add_trace(
        state,
        step=9,
        task="Update customer profile",
        status="completed",
        result="Customer profile updated",
    )


# ==========================================
# ROUTING
# ==========================================

def route_after_safety(state: AgroState) -> str:
    intent = state["intent"]
    safety_result = state["safety_result"]

    if safety_result.get("escalation_required", False):
        return "escalation"
    if intent in ["complaint", "pesticide_safety"]:
        return "escalation"
    if intent == "order_status":
        return "order"
    if intent in ["crop_diagnosis", "product_question"]:
        return "knowledge"
    return "general"


# ==========================================
# GRAPH BUILD
# ==========================================

workflow = StateGraph(AgroState)

workflow.add_node("load_customer_profile", load_customer_profile_node)
workflow.add_node("image_diagnosis", image_diagnosis_node)
workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("check_safety", safety_check_node)
workflow.add_node("init_defaults", init_defaults_node)
workflow.add_node("product_and_rag", product_and_rag_node)
workflow.add_node("order_lookup", order_lookup_node)
workflow.add_node("escalation", escalation_node)
workflow.add_node("general", general_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_node("save_case", save_case_node)
workflow.add_node("update_customer_profile", update_customer_profile_node)

workflow.set_entry_point("load_customer_profile")

workflow.add_edge("load_customer_profile", "image_diagnosis")
workflow.add_edge("image_diagnosis", "classify_intent")
workflow.add_edge("classify_intent", "check_safety")
workflow.add_edge("check_safety", "init_defaults")

workflow.add_conditional_edges(
    "init_defaults",
    route_after_safety,
    {
        "knowledge": "product_and_rag",
        "order": "order_lookup",
        "escalation": "escalation",
        "general": "general",
    },
)

workflow.add_edge("product_and_rag", "generate_response")
workflow.add_edge("order_lookup", "generate_response")
workflow.add_edge("escalation", "generate_response")
workflow.add_edge("general", "generate_response")

workflow.add_edge("generate_response", "save_case")
workflow.add_edge("save_case", "update_customer_profile")
workflow.add_edge("update_customer_profile", END)

agro_graph = workflow.compile()


def run_agro_graph(
    customer_id: str,
    message: str,
    image_path: Optional[str] = None,
    image_filename: Optional[str] = None,
) -> Dict[str, Any]:
    initial_state: AgroState = {
        "customer_id": customer_id,
        "message": message or "",
        "image_path": image_path,
        "image_filename": image_filename,
        "execution_trace": [],
    }

    result = agro_graph.invoke(initial_state)

    saved_case = result.get("saved_case", {})
    product_result = result.get("product_result", default_product_result())
    safety_result = result.get("safety_result", {})
    rag_result = result.get("rag_result", default_rag_result())
    order_result = result.get("order_result", default_order_result())
    image_result = result.get("image_result", default_image_result())

    detected_crop = product_result.get("detected_crop") or _image_crop(image_result)

    detected_issue = product_result.get("detected_issue") or _image_issue(image_result)

    human_review_required = bool(
        safety_result.get("escalation_required", False)
        or _image_needs_review(image_result)
    )

    return {
        "customer_id": result.get("customer_id"),
        "received_message": result.get("message"),
        "message": result.get("message"),
        "intent": result.get("intent"),
        "raw_intent": result.get("raw_intent"),
        "response": result.get("ai_response"),
        "llm_status": result.get("llm_status"),
        "execution_trace": result.get("execution_trace", []),
        "debug_rule_based_response": result.get("response_text"),

        "image_uploaded": image_result.get("image_uploaded", False),
        "image_filename": result.get("image_filename"),
        "image_result": image_result,

        "recommended_product": product_result.get("recommended_product"),
        "product_id": product_result.get("product_id"),
        "product_reason": product_result.get("reason"),
        "product_confidence": product_result.get("confidence"),
        "product_result": product_result,

        "risk_level": safety_result.get("risk_level"),
        "safety_reason": safety_result.get("reason"),
        "escalation_required": safety_result.get("escalation_required", False),
        "human_review_required": human_review_required,

        "case_saved": saved_case.get("case_saved"),
        "case_id": saved_case.get("case_id"),
        "case_duplicate": saved_case.get("case_duplicate"),
        "case_save_reason": saved_case.get("reason"),

        "customer_profile": result.get("customer_profile"),
        "updated_customer_profile": result.get("updated_customer_profile"),
        "profile_updated": True,
        "profile_update_reason": "Customer profile updated",

        "detected_crop": detected_crop,
        "detected_issue": detected_issue,

        "rag": rag_result,
        "rag_result": rag_result,

        "order": order_result,
        "order_result": order_result,
        "order_id": order_result.get("order_id"),
        "order_status": order_result.get("status"),

        "error": None,
    }