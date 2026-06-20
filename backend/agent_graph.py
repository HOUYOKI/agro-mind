from typing import Any, Dict, Optional, TypedDict
import importlib

from langgraph.graph import StateGraph, END

from backend.tools.intent_classifier import classify_intent, normalize_intent
from backend.tools.safety_checker import check_safety
from backend.tools.product_recommender import recommend_product
from backend.tools.rag_retriever import retrieve_agronomy_knowledge
from backend.tools.llm_agent import ask_agro_mind
from backend.tools.customer_profile import (
    summarize_customer_profile,
    update_customer_profile,
)


class AgroState(TypedDict, total=False):
    customer_id: str
    message: str

    intent: str
    raw_intent: str

    risk_level: str
    safety_reason: str
    escalation_required: bool
    human_review_required: bool

    rag_result: Dict[str, Any]
    product_result: Dict[str, Any]
    order_result: Dict[str, Any]
    customer_profile_summary: str
    updated_customer_profile: Dict[str, Any]

    response: str
    llm_status: str

    recommended_product: Optional[str]
    product_id: Optional[str]
    product_reason: Optional[str]
    product_confidence: Optional[float]

    detected_crop: Any
    detected_issue: Any

    order_id: Optional[str]
    order_status: Optional[str]

    error: Optional[str]


def _safe_get(data: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default

    return data.get(key, default)


def _call_order_lookup(customer_id: str, message: str) -> Dict[str, Any]:
    """
    Dynamic lookup so this file does not break if the logistics tool function name differs.
    """
    try:
        module = importlib.import_module("backend.tools.logistics_lookup")

        for function_name in [
            "lookup_order_status",
            "lookup_order",
            "get_order_status",
            "check_order_status",
        ]:
            function = getattr(module, function_name, None)

            if callable(function):
                try:
                    return function(customer_id=customer_id, message=message)
                except TypeError:
                    try:
                        return function(customer_id, message)
                    except TypeError:
                        return function(message)

    except Exception as error:
        return {
            "found": False,
            "status": "error",
            "error": str(error),
        }

    return {
        "found": False,
        "status": "not_configured",
        "message": "Order lookup tool is not configured.",
    }


def _extract_order_fields(order_result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(order_result, dict):
        return {
            "order_id": None,
            "order_status": None,
        }

    return {
        "order_id": (
            order_result.get("order_id")
            or order_result.get("id")
            or order_result.get("tracking_id")
        ),
        "order_status": (
            order_result.get("order_status")
            or order_result.get("status")
            or order_result.get("delivery_status")
        ),
    }


def _build_customer_fallback_response(state: AgroState) -> str:
    intent = state.get("intent", "general_question")
    risk_level = state.get("risk_level", "low")

    if risk_level == "high":
        return (
            "This looks like a high-risk safety case. Do not ingest, touch, or apply any chemical product. "
            "Please contact emergency services, poison control, or a qualified professional immediately. "
            "This case has been flagged for human review."
        )

    if risk_level == "medium":
        return (
            "This case may involve pesticide safety, exposure, crop damage, or another sensitive issue. "
            "Please check the product label and have a human agricultural expert review the case before taking action."
        )

    if intent == "order_status":
        order_status = state.get("order_status")
        order_id = state.get("order_id")

        if order_status:
            if order_id:
                return f"Your order {order_id} is currently marked as: {order_status}."
            return f"Your order is currently marked as: {order_status}."

        return "I could not find a matching order status. Please check the order ID or contact support."

    product_name = state.get("recommended_product")

    if intent in {"crop_diagnosis", "product_question"}:
        if product_name:
            return (
                f"The closest product match is {product_name}. "
                "Please confirm the diagnosis and follow the official product label before using it."
            )

        return (
            "I could not find a reliable product match from the knowledge base. "
            "Please provide more crop symptoms or ask a human agronomist to review the case."
        )

    return (
        "I processed your request, but I could not generate a detailed response right now. "
        "Please provide more details or request human review if the case is urgent."
    )


def classify_intent_node(state: AgroState) -> AgroState:
    raw_intent = classify_intent(state.get("message", ""))
    intent = normalize_intent(raw_intent)

    state["raw_intent"] = raw_intent
    state["intent"] = intent

    return state


def safety_node(state: AgroState) -> AgroState:
    safety = check_safety(
        user_query=state.get("message", ""),
        intent=state.get("intent", "general_question"),
    )

    risk_level = safety.get("risk_level", "low")
    escalation_required = bool(safety.get("escalation_required", False))

    state["risk_level"] = risk_level
    state["safety_reason"] = safety.get("reason", "Safe.")
    state["escalation_required"] = escalation_required
    state["human_review_required"] = escalation_required or risk_level in {"medium", "high"}

    return state


def customer_profile_node(state: AgroState) -> AgroState:
    customer_id = state.get("customer_id", "unknown")

    try:
        state["customer_profile_summary"] = summarize_customer_profile(customer_id)
    except Exception as error:
        state["customer_profile_summary"] = "No customer profile found."
        state["error"] = f"Customer profile summary failed: {error}"

    return state


def route_after_safety(state: AgroState) -> str:
    risk_level = state.get("risk_level", "low")
    intent = state.get("intent", "general_question")

    if risk_level == "high":
        return "generate_response"

    if intent == "order_status":
        return "order_lookup"

    if intent in {"crop_diagnosis", "product_question"}:
        return "rag_lookup"

    if intent == "pesticide_safety":
        return "generate_response"

    if intent == "complaint":
        return "generate_response"

    return "generate_response"


def rag_lookup_node(state: AgroState) -> AgroState:
    message = state.get("message", "")
    intent = state.get("intent", "general_question")

    query_type = "general"

    if intent == "crop_diagnosis":
        query_type = "disease"

    try:
        rag_result = retrieve_agronomy_knowledge(
            query=message,
            query_type=query_type,
            n_results=3,
        )
    except Exception as error:
        rag_result = {
            "rag_used": False,
            "found": False,
            "summary": "RAG retrieval failed.",
            "sources": [],
            "confidence": 0.0,
            "status": "error",
            "error": str(error),
        }

    state["rag_result"] = rag_result

    return state


def product_recommendation_node(state: AgroState) -> AgroState:
    risk_level = state.get("risk_level", "low")

    if risk_level in {"medium", "high"}:
        state["product_result"] = {
            "recommended_product": None,
            "reason": "Product recommendation disabled because this case requires safety review.",
            "safety_note": "Human review required before any product use.",
            "detected_crop": [],
            "detected_issue": [],
            "confidence": 0.0,
            "status": "disabled_for_safety",
        }
        state["recommended_product"] = None
        state["product_id"] = None
        state["product_reason"] = "Product recommendation disabled because this case requires safety review."
        state["product_confidence"] = 0.0
        return state

    try:
        product_result = recommend_product(state.get("message", ""))

    except Exception as error:
        product_result = {
            "recommended_product": None,
            "reason": "Product recommendation failed.",
            "safety_note": "No product recommendation should be made until retrieval is working.",
            "detected_crop": [],
            "detected_issue": [],
            "confidence": 0.0,
            "status": "error",
            "error": str(error),
        }

    state["product_result"] = product_result

    state["recommended_product"] = product_result.get("recommended_product")
    state["product_id"] = product_result.get("product_id")
    state["product_reason"] = product_result.get("reason")
    state["product_confidence"] = product_result.get("confidence")
    state["detected_crop"] = product_result.get("detected_crop")
    state["detected_issue"] = product_result.get("detected_issue")

    return state


def order_lookup_node(state: AgroState) -> AgroState:
    order_result = _call_order_lookup(
        customer_id=state.get("customer_id", "unknown"),
        message=state.get("message", ""),
    )

    state["order_result"] = order_result

    order_fields = _extract_order_fields(order_result)

    state["order_id"] = order_fields.get("order_id")
    state["order_status"] = order_fields.get("order_status")

    return state


def memory_update_node(state: AgroState) -> AgroState:
    customer_id = state.get("customer_id", "unknown")

    try:
        update_data = {
            "last_intent": state.get("intent"),
            "crop": state.get("detected_crop"),
            "possible_issue": state.get("detected_issue"),
            "recommended_product": state.get("recommended_product"),
            "order_id": state.get("order_id"),
            "escalation_required": state.get("escalation_required", False),
            "human_escalation_requested": state.get("human_review_required", False),
        }

        updated_profile = update_customer_profile(customer_id, update_data)
        state["updated_customer_profile"] = updated_profile

    except Exception as error:
        state["error"] = f"Customer profile update failed: {error}"

    return state


def generate_response_node(state: AgroState) -> AgroState:
    rag_result = state.get("rag_result", {}) or {}
    product_result = state.get("product_result", {}) or {}
    order_result = state.get("order_result", {}) or {}

    compact_prompt = f"""
Customer message:
{state.get("message", "")}

Intent:
{state.get("intent", "general_question")}

Safety:
Risk level: {state.get("risk_level", "low")}
Reason: {state.get("safety_reason", "Safe.")}
Escalation required: {state.get("escalation_required", False)}

Customer profile:
{state.get("customer_profile_summary", "No customer profile found.")}

RAG result:
{rag_result}

Product result:
{product_result}

Order result:
{order_result}

Write the final customer reply.

Rules:
- Be short and natural.
- Do not use email style.
- Do not invent facts.
- Do not recommend a product if product_result has no recommended_product.
- Do not recommend a product for medium/high risk safety cases.
- For pesticide/chemical/food safety, avoid exact dosage, dilution, harvest interval, or safety guarantees unless explicitly shown in tool results.
- If human review is required, say so clearly.
"""

    try:
        response = ask_agro_mind(compact_prompt)
        state["response"] = response
        state["llm_status"] = "success"

    except Exception as error:
        state["response"] = _build_customer_fallback_response(state)
        state["llm_status"] = f"fallback: {error}"

    if not state.get("response"):
        state["response"] = _build_customer_fallback_response(state)
        state["llm_status"] = "fallback_empty_response"

    return state


def route_after_rag(state: AgroState) -> str:
    return "product_recommendation"


workflow = StateGraph(AgroState)

workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("safety", safety_node)
workflow.add_node("customer_profile", customer_profile_node)
workflow.add_node("rag_lookup", rag_lookup_node)
workflow.add_node("product_recommendation", product_recommendation_node)
workflow.add_node("order_lookup", order_lookup_node)
workflow.add_node("memory_update", memory_update_node)
workflow.add_node("generate_response", generate_response_node)

workflow.set_entry_point("classify_intent")

workflow.add_edge("classify_intent", "safety")
workflow.add_edge("safety", "customer_profile")

workflow.add_conditional_edges(
    "customer_profile",
    route_after_safety,
    {
        "rag_lookup": "rag_lookup",
        "order_lookup": "order_lookup",
        "generate_response": "generate_response",
    },
)

workflow.add_conditional_edges(
    "rag_lookup",
    route_after_rag,
    {
        "product_recommendation": "product_recommendation",
    },
)

workflow.add_edge("product_recommendation", "memory_update")
workflow.add_edge("order_lookup", "memory_update")
workflow.add_edge("memory_update", "generate_response")
workflow.add_edge("generate_response", END)

agro_graph = workflow.compile()


def run_agro_graph(customer_id: str, message: str) -> Dict[str, Any]:
    initial_state: AgroState = {
        "customer_id": customer_id,
        "message": message,
        "intent": "general_question",
        "raw_intent": "general_question",
        "risk_level": "low",
        "safety_reason": "Safe.",
        "escalation_required": False,
        "human_review_required": False,
        "rag_result": {},
        "product_result": {},
        "order_result": {},
        "customer_profile_summary": "",
        "response": "",
        "llm_status": "not_started",
        "recommended_product": None,
        "product_id": None,
        "product_reason": None,
        "product_confidence": None,
        "detected_crop": None,
        "detected_issue": None,
        "order_id": None,
        "order_status": None,
    }

    final_state = agro_graph.invoke(initial_state)

    return {
        "customer_id": customer_id,
        "message": message,

        "intent": final_state.get("intent", "general_question"),
        "raw_intent": final_state.get("raw_intent", final_state.get("intent", "general_question")),

        "risk_level": final_state.get("risk_level", "low"),
        "safety_reason": final_state.get("safety_reason", "Safe."),
        "escalation_required": final_state.get("escalation_required", False),
        "human_review_required": final_state.get("human_review_required", False),

        "response": final_state.get("response", ""),
        "llm_status": final_state.get("llm_status", "unknown"),

        "rag": final_state.get("rag_result", {}),
        "rag_result": final_state.get("rag_result", {}),

        "recommended_product": final_state.get("recommended_product"),
        "product_id": final_state.get("product_id"),
        "product_reason": final_state.get("product_reason"),
        "product_confidence": final_state.get("product_confidence"),
        "product_result": final_state.get("product_result", {}),

        "detected_crop": final_state.get("detected_crop"),
        "detected_issue": final_state.get("detected_issue"),

        "order_id": final_state.get("order_id"),
        "order_status": final_state.get("order_status"),
        "order_result": final_state.get("order_result", {}),

        "customer_profile": final_state.get("updated_customer_profile"),
        "updated_customer_profile": final_state.get("updated_customer_profile"),

        "error": final_state.get("error"),
    }