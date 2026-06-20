from typing import TypedDict, Dict, Any, List, Optional

from langgraph.graph import StateGraph, END

from backend.tools.intent_classifier import classify_intent
from backend.tools.safety_checker import check_safety
from backend.tools.product_recommender import recommend_product
from backend.tools.logistics_lookup import lookup_order
from backend.tools.case_memory import save_case
from backend.tools.llm_agent import ask_agro_mind
from backend.tools.rag_retriever import retrieve_agronomy_knowledge
from backend.tools.customer_profile import (
    get_customer_profile,
    update_customer_profile,
    summarize_customer_profile,
)


class AgroState(TypedDict, total=False):
    customer_id: str
    message: str

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


def add_trace(
    state: AgroState,
    step: int,
    task: str,
    status: str,
    result: Any = None,
) -> AgroState:
    trace = state.get("execution_trace", [])
    trace.append(
        {
            "step": step,
            "task": task,
            "status": status,
            "result": result,
        }
    )
    state["execution_trace"] = trace
    return state


def normalize_intent(raw_intent: str) -> str:
    """
    Keeps the graph stable even if the intent classifier returns a synonym.
    """
    value = (raw_intent or "").strip().lower()

    mapping = {
        "crop": "crop_diagnosis",
        "diagnosis": "crop_diagnosis",
        "crop_problem": "crop_diagnosis",
        "crop_diagnosis": "crop_diagnosis",

        "product": "product_question",
        "product_recommendation": "product_question",
        "product_question": "product_question",

        "pesticide": "pesticide_safety",
        "safety": "pesticide_safety",
        "pesticide_safety": "pesticide_safety",

        "order": "order_status",
        "order_lookup": "order_status",
        "order_status": "order_status",

        "complaint": "complaint",
        "complaints": "complaint",

        "general": "general_question",
        "general_question": "general_question",
    }

    return mapping.get(value, "general_question")


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


def classify_intent_node(state: AgroState) -> AgroState:
    raw_intent = classify_intent(state["message"])
    intent = normalize_intent(raw_intent)

    state["raw_intent"] = raw_intent
    state["intent"] = intent

    return add_trace(
        state,
        step=2,
        task="Classify customer intent",
        status="completed",
        result=intent,
    )


def safety_check_node(state: AgroState) -> AgroState:
    safety_result = check_safety(state["message"], state["intent"])
    state["safety_result"] = safety_result

    return add_trace(
        state,
        step=3,
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

    if (
        intent in ["crop_diagnosis", "product_question"]
        and not safety_result.get("escalation_required", False)
    ):
        try:
            product_result = recommend_product(state["message"])
            if product_result:
                state["product_result"].update(product_result)
        except Exception as error:
            state["product_result"] = default_product_result()
            state["product_result"]["reason"] = f"Product recommendation failed: {str(error)}"

    if (
        intent in ["crop_diagnosis", "product_question", "general_question"]
        and not safety_result.get("escalation_required", False)
    ):
        try:
            rag_result = retrieve_agronomy_knowledge(state["message"], intent)
            if rag_result:
                state["rag_result"].update(rag_result)
        except Exception as error:
            state["rag_result"] = default_rag_result()
            state["rag_result"]["summary"] = f"RAG retrieval failed: {str(error)}"
            state["rag_result"]["status"] = "error"

    state = add_trace(
        state,
        step=4,
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
        step=5,
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
        order_result = lookup_order(
            state["message"],
            state["customer_id"],
        )
        if order_result:
            state["order_result"].update(order_result)

    except Exception as error:
        state["order_result"] = default_order_result()
        state["order_result"]["reason"] = f"Order lookup failed: {str(error)}"

    return add_trace(
        state,
        step=4,
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

    if risk_level == "high":
        state["product_result"]["reason"] = "High-risk safety case. Product recommendation disabled."
    elif intent == "complaint":
        state["product_result"]["reason"] = "Complaint or damage claim requires human review. Product recommendation disabled."
    else:
        state["product_result"]["reason"] = "Product recommendation not needed for this intent."

    state = add_trace(
        state,
        step=4,
        task="Retrieve agronomy knowledge if needed",
        status="skipped",
        result="Skipped due to safety or escalation risk",
    )

    state = add_trace(
        state,
        step=5,
        task="Run product recommendation if needed",
        status="skipped",
        result=None,
    )

    return state


def general_node(state: AgroState) -> AgroState:
    safety_result = state["safety_result"]

    if not safety_result.get("escalation_required", False):
        try:
            rag_result = retrieve_agronomy_knowledge(state["message"], state["intent"])
            if rag_result:
                state["rag_result"].update(rag_result)
        except Exception as error:
            state["rag_result"] = default_rag_result()
            state["rag_result"]["summary"] = f"RAG retrieval failed: {str(error)}"
            state["rag_result"]["status"] = "error"

    return add_trace(
        state,
        step=4,
        task="Handle general question",
        status="completed",
        result=(
            state["rag_result"].get("summary")
            if state["rag_result"].get("found")
            else "General response path"
        ),
    )


def build_rule_based_response(state: AgroState) -> str:
    """
    Safety net only. Normal response should come from Qwen.
    """
    intent = state["intent"]
    safety_result = state["safety_result"]
    product_result = state["product_result"]
    order_result = state["order_result"]

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
            "I’m sorry this happened. Because this involves a complaint or possible crop damage, "
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

    fallback_response = build_rule_based_response(state)
    state["response_text"] = fallback_response

    message = state["message"]

    final_prompt = f"""
You are writing the final customer-facing chatbot response for Agro-Mind.

Customer current message:
{message}

Customer profile context:
{state.get("customer_profile_summary", "No customer profile found.")}

Tool results:

Intent classifier:
- Raw intent: {state.get("raw_intent")}
- Normalized intent: {state.get("intent")}

Safety checker:
- Risk level: {safety_result.get("risk_level")}
- Safety reason: {safety_result.get("reason")}
- Escalation required: {safety_result.get("escalation_required")}

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
Answer in the same language as the customer's current message.
Ignore preferred_language from the customer profile.
Ignore the language of customer profile memory, retrieved product data, product names, and Chinese metadata.
If the customer message is English, answer in English.
If the customer message is Arabic, answer in Arabic.
If the customer message is Chinese, answer in Chinese.
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
13. Avoid saying a product “will effectively control,” “can effectively manage,” or guarantees treatment. Use cautious wording like “may help,” “could be relevant,” or “may support management,” and recommend confirming the diagnosis first.
"""

    try:
        state["ai_response"] = ask_agro_mind(
            final_prompt,
            original_user_message=message,
        )
        state["llm_status"] = "success"

    except Exception as error:
        print(f"LLM error: {error}")
        state["ai_response"] = fallback_response
        state["llm_status"] = "failed_fallback_used"

    return add_trace(
        state,
        step=6,
        task="Generate final response with Qwen",
        status=state["llm_status"],
        result=(
            "Final chatbot response generated"
            if state["llm_status"] == "success"
            else "Fallback rule-based response used"
        ),
    )


def _to_csv(value):
    """Convert a list to comma-separated string; pass str/None through unchanged."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v is not None) or None
    return value


def save_case_node(state: AgroState) -> AgroState:
    saved_case = save_case(
        customer_id=state["customer_id"],
        message=state["message"],
        intent=state["intent"],
        possible_issue=_to_csv(state["product_result"].get("detected_issue")),
        recommended_product=state["product_result"].get("recommended_product"),
        risk_level=state["safety_result"].get("risk_level", "low"),
        escalation_required=state["safety_result"].get("escalation_required", False),
        order_id=state["order_result"].get("order_id"),
        order_status=state["order_result"].get("status"),
    )

    state["saved_case"] = saved_case

    return add_trace(
        state,
        step=7,
        task="Save support case",
        status="completed" if saved_case.get("case_saved") else "skipped",
        result=saved_case.get("reason"),
    )


def update_customer_profile_node(state: AgroState) -> AgroState:
    updated_profile = update_customer_profile(
        state["customer_id"],
        {
            "last_intent": state["intent"],
            "last_message": state["message"],
            "crop": state["product_result"].get("detected_crop"),
            "possible_issue": state["product_result"].get("detected_issue"),
            "recommended_product": state["product_result"].get("recommended_product"),
            "risk_level": state["safety_result"].get("risk_level"),
            "order_id": state["order_result"].get("order_id"),
            "order_status": state["order_result"].get("status"),
            "human_escalation_requested": state["safety_result"].get("escalation_required", False),
            "escalation_required": state["safety_result"].get("escalation_required", False),
        },
    )

    state["updated_customer_profile"] = updated_profile

    return add_trace(
        state,
        step=8,
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

workflow.add_edge("load_customer_profile", "classify_intent")
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


def run_agro_graph(customer_id: str, message: str) -> Dict[str, Any]:
    initial_state: AgroState = {
        "customer_id": customer_id,
        "message": message,
        "execution_trace": [],
    }

    result = agro_graph.invoke(initial_state)

    saved_case = result.get("saved_case", {})

    product_result = result.get("product_result", default_product_result())
    safety_result = result.get("safety_result", {})
    rag_result = result.get("rag_result", default_rag_result())
    order_result = result.get("order_result", default_order_result())

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

        "recommended_product": product_result.get("recommended_product"),
        "product_id": product_result.get("product_id"),
        "product_reason": product_result.get("reason"),
        "product_confidence": product_result.get("confidence"),
        "product_result": product_result,

        "risk_level": safety_result.get("risk_level"),
        "safety_reason": safety_result.get("reason"),
        "escalation_required": safety_result.get("escalation_required", False),
        "human_review_required": safety_result.get("escalation_required", False),

        "case_saved": saved_case.get("case_saved"),
        "case_id": saved_case.get("case_id"),
        "case_duplicate": saved_case.get("case_duplicate"),
        "case_save_reason": saved_case.get("reason"),

        "customer_profile": result.get("customer_profile"),
        "updated_customer_profile": result.get("updated_customer_profile"),
        "profile_updated": True,
        "profile_update_reason": "Customer profile updated",

        "detected_crop": product_result.get("detected_crop"),
        "detected_issue": product_result.get("detected_issue"),

        "rag": rag_result,
        "rag_result": rag_result,

        "order": order_result,
        "order_result": order_result,

        "order_id": order_result.get("order_id"),
        "order_status": order_result.get("status"),

        "error": None,
    }