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
from backend.tools.langsmith_logger import log_important_case


class AgroState(TypedDict, total=False):
    customer_id: str
    message: str

    intent: str
    safety_result: Dict[str, Any]
    langsmith_logged: bool
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
    intent = classify_intent(state["message"])
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
        result=safety_result["risk_level"],
    )

def langsmith_logging_node(state: AgroState) -> AgroState:
    safety = state["safety_result"]
    should_log = (
        safety["risk_level"] in ["medium", "high"]
        or safety["escalation_required"]
        or state["intent"] == "complaint"
    )
    if should_log:
        result = log_important_case(
            customer_id=state["customer_id"],
            message=state["message"],
            intent=state["intent"],
            risk_level=safety["risk_level"],
            escalation_required=
            safety["escalation_required"]
        )
        state["langsmith_logged"] = result

    else:
        state["langsmith_logged"] = False

    return add_trace(
        state,
        step=4,
        task="Log important case to LangSmith",
        status="completed"
        if should_log else "skipped",
        result=(
            "Case logged"
            if should_log
            else "Routine case - ignored"
        )
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
        and not safety_result["escalation_required"]
    ):
        state["product_result"] = recommend_product(state["message"])

    if (
        intent in ["crop_diagnosis", "product_question", "general_question"]
        and not safety_result["escalation_required"]
    ):
        state["rag_result"] = retrieve_agronomy_knowledge(state["message"], intent)

    state = add_trace(
        state,
        step=4,
        task="Retrieve agronomy knowledge if needed",
        status="completed" if state["rag_result"]["rag_used"] else "skipped",
        result=(
            state["rag_result"]["summary"]
            if state["rag_result"]["found"]
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
            and not safety_result["escalation_required"]
            else "skipped"
        ),
        result=state["product_result"]["recommended_product"],
    )

    return state


def order_lookup_node(state: AgroState) -> AgroState:
    state["order_result"] = lookup_order(
        state["message"],
        state["customer_id"],
    )

    return add_trace(
        state,
        step=4,
        task="Run order lookup if needed",
        status="completed",
        result=state["order_result"]["status"],
    )


def escalation_node(state: AgroState) -> AgroState:
    state["rag_result"] = default_rag_result()
    state["product_result"] = default_product_result()
    state["order_result"] = default_order_result()

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
    intent = state["intent"]
    safety_result = state["safety_result"]

    if intent == "general_question" and not safety_result["escalation_required"]:
        state["rag_result"] = retrieve_agronomy_knowledge(state["message"], intent)

    return add_trace(
        state,
        step=4,
        task="Handle general question",
        status="completed",
        result=(
            state["rag_result"]["summary"]
            if state["rag_result"]["found"]
            else "General response path"
        ),
    )


def build_rule_based_response(state: AgroState) -> str:
    intent = state["intent"]
    safety_result = state["safety_result"]
    product_result = state["product_result"]
    order_result = state["order_result"]

    response_text = (
        f"Intent: {intent}\n\n"
        f"Risk level: {safety_result['risk_level']}\n"
        f"Safety reason: {safety_result['reason']}\n\n"
    )

    if product_result["recommended_product"]:
        response_text += (
            f"Detected crop: {product_result['detected_crop']}\n"
            f"Possible issue: {product_result['detected_issue']}\n"
            f"Possible product: {product_result['recommended_product']}\n"
            f"Product reason: {product_result['reason']}\n"
            f"Safety note: {product_result['safety_note']}\n\n"
            "Important: Please confirm the diagnosis before applying any pesticide."
        )

    elif intent != "order_status":
        if safety_result["escalation_required"]:
            response_text += (
                "This case should be reviewed by a human support or agronomy expert."
            )
        else:
            response_text += "No product recommendation was made for this message."

    if intent == "order_status":
        if order_result["order_found"]:
            response_text += (
                f"Order status:\n"
                f"Order ID: {order_result['order_id']}\n"
                f"Status: {order_result['status']}\n"
                f"ETA: {order_result['eta']}\n"
                f"Tracking number: {order_result['tracking_number']}\n"
                f"Lookup reason: {order_result['reason']}"
            )
        else:
            response_text += (
                f"Order status:\n"
                f"{order_result['reason']}"
            )

    return response_text

def enforce_final_safety_response(state: AgroState, ai_response: str) -> str:
    message = state["message"].lower()
    product_name = state["product_result"].get("recommended_product")

    food_safety_keywords = [
        "eat",
        "edible",
        "consume",
        "harvest",
        "one day",
        "after spraying",
        "sprayed pesticide",
    ]

    banned_response_phrases = [
        "safety checker",
        "tool",
        "classifier",
        "guardrail",
        "rag",
        "debug",
        "generally, you should wait",
        "wait at least",
        "dilution",
        "dilution ratio",
        "before 10",
        "after 4",
        "application frequency",
        "pre-harvest interval",
        "safety interval",
        "apply before",
        "apply after",
        "can control",
        "can effectively",
        "will effectively",
    ]

    is_food_safety_question = any(keyword in message for keyword in food_safety_keywords)
    contains_banned_phrase = any(
        phrase in ai_response.lower()
        for phrase in banned_response_phrases
    )

    if is_food_safety_question:
        return (
            "I can’t confirm whether the tomatoes are safe to eat from the message alone. "
            "Please check the exact pesticide label for the required pre-harvest interval and safety instructions. "
            "If you are unsure, do not eat the crop until a qualified agricultural expert confirms it."
        )

    if contains_banned_phrase and product_name:
        return (
            f"{product_name} could be relevant as a possible support product, but the crop issue should be confirmed first. "
            "Please follow the official product label for all application and safety instructions. "
            "Since this involves crop treatment, consult a qualified agricultural expert before applying it."
        )

    if contains_banned_phrase:
        return (
            "For this case, please avoid making treatment decisions from the message alone. "
            "Follow the official product label for any agricultural product and consult a qualified agricultural expert for confirmation."
        )

    return ai_response

def generate_response_node(state: AgroState) -> AgroState:
    product_result = state["product_result"]
    order_result = state["order_result"]
    rag_result = state["rag_result"]
    safety_result = state["safety_result"]

    response_text = build_rule_based_response(state)
    state["response_text"] = response_text

    llm_prompt = f"""
You are writing the final chatbot response for Agro-Mind.

Customer message:
{state["message"]}

Customer profile context:
{state["customer_profile_summary"]}

Important language rule:
Agro-Mind supports English and Chinese customer conversations.
Choose the response language based on the customer's current message, not the saved customer profile.
If the customer's current message is written in English, answer in English.
If the customer's current message is written in Chinese, answer in Chinese.
If the message is mixed or unclear, use the main language of the customer's current message.
Do not switch language because of preferred_language in the customer profile.
Do not explain language choice to the customer.

Important profile rules:
Use the customer profile only as background context for crops, issues, orders, complaints, and support history.
Do not reveal internal labels like customer_segment or upsell_opportunity directly to the customer.

Tool results:

Intent classifier:
- Intent: {state["intent"]}

Safety checker:
- Risk level: {safety_result["risk_level"]}
- Safety reason: {safety_result["reason"]}
- Escalation required: {safety_result["escalation_required"]}

Product recommender:
- Detected crop: {product_result["detected_crop"]}
- Detected issue: {product_result["detected_issue"]}
- Recommended product: {product_result["recommended_product"]}
- Product reason: {product_result["reason"]}
- Safety note: {product_result["safety_note"]}

RAG retriever:
- RAG used: {rag_result["rag_used"]}
- Knowledge found: {rag_result["found"]}
- Knowledge summary: {rag_result["summary"]}
- Sources: {rag_result["sources"]}
- Confidence: {rag_result["confidence"]}
- RAG status: {rag_result["status"]}

Order lookup:
- Order found: {order_result["order_found"]}
- Order ID: {order_result["order_id"]}
- Status: {order_result["status"]}
- ETA: {order_result["eta"]}
- Tracking number: {order_result["tracking_number"]}
- Order reason: {order_result["reason"]}

Write the final customer-facing chatbot answer.

Rules:
1. Do not greet with "Dear", "Hello C001", or write like an email.
2. Do not end with "Best regards" or "Agro-Mind Team".
3. Do not mention internal words like "intent", "tool result", "risk_level", "RAG", "debug", "customer_segment", or "upsell_opportunity".
4. Do not invent anything not shown in the tool results.
5. If no exact product match exists, say that clearly.
6. If the recommended product is only a general support product, do not present it as a guaranteed solution.
7. If escalation_required is True, say that a human expert should review or confirm the case.
8. For pesticide, chemical, harvest, dosage, or food safety, NEVER give exact waiting periods, dosage numbers, dilution ratios, application intervals, number of applications, safety guarantees, or "it is safe after X days" in the final customer answer, even if those details appear in retrieved product text. Instead, tell the customer to follow the official product label and consult a qualified agricultural expert.
9. You may mention the recommended product name and general purpose, but do not provide exact dosage, dilution, timing, safety interval, application frequency, application time of day, or detailed application instructions.
10. If the customer asks whether food can be eaten after spraying, say you cannot confirm safety from the message alone. Tell them to check the specific product label for the pre-harvest interval/waiting period and consult a human agricultural expert.
11. If retrieved knowledge is found, use it to support the answer, but do not pretend it is a final diagnosis.
12. Keep the answer between 3 and 6 short sentences. Be cautious and avoid detailed chemical instructions.
13. Sound like a helpful chatbot, not a formal email.
14. Never use preferred_language from the customer profile to decide the answer language.
15. The response language must follow the customer's current message.
16. If the current message is English, answer in English.
17. If the current message is Chinese, answer in Chinese.
18. If the current message is mixed or unclear, use the main language of the current message.
19. Do not mention language rules to the customer.
20. Avoid saying a product “will effectively control,” “can effectively manage,” “can control,” or guarantees treatment. Use cautious wording like “may help,” “could be relevant,” or “may support management,” and always recommend confirming the diagnosis first.
21. Never mention "safety checker", "tool", "classifier", "guardrail", "RAG", "debug", or any internal system name in the customer-facing answer.
"""

    try:
        raw_response = ask_agro_mind(llm_prompt)
        state["ai_response"] = enforce_final_safety_response(state, raw_response)
        state["llm_status"] = "completed"

    except Exception as error:
        print(f"LLM error: {error}")
        state["ai_response"] = response_text
        state["llm_status"] = "failed_fallback_used"

    return add_trace(
        state,
        step=6,
        task="Generate final response with Qwen",
        status=state["llm_status"],
        result=(
            "Final chatbot response generated"
            if state["llm_status"] == "completed"
            else "Fallback rule-based response used"
        ),
    )


def save_case_node(state: AgroState) -> AgroState:
    saved_case = save_case(
        customer_id=state["customer_id"],
        message=state["message"],
        order_id=state["order_result"]["order_id"],
        order_status=state["order_result"]["status"],
    )

    state["saved_case"] = saved_case

    return add_trace(
        state,
        step=7,
        task="Save support case",
        status="completed" if saved_case["case_saved"] else "skipped",
        result=saved_case["reason"],
    )


def update_customer_profile_node(state: AgroState) -> AgroState:
    updated_profile = update_customer_profile(
        state["customer_id"],
        {
            "last_intent": state["intent"],
            "last_message": state["message"],
            "crop": state["product_result"]["detected_crop"],
            "possible_issue": state["product_result"]["detected_issue"],
            "recommended_product": state["product_result"]["recommended_product"],
            "risk_level": state["safety_result"]["risk_level"],
            "order_id": state["order_result"]["order_id"],
            "order_status": state["order_result"]["status"],
            "escalation_required": state["safety_result"]["escalation_required"],
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

    if safety_result["escalation_required"] or intent in ["complaint", "pesticide_safety"]:
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
workflow.add_node("langsmith_logging",langsmith_logging_node)
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
workflow.add_edge("classify_intent","check_safety")
workflow.add_edge("check_safety","langsmith_logging")
workflow.add_edge("langsmith_logging","init_defaults")

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

    saved_case = result["saved_case"]

    return {
        "customer_id": result["customer_id"],
        "received_message": result["message"],
        "intent": result["intent"],

        "response": result["ai_response"],
        "execution_trace": result["execution_trace"],
        "debug_rule_based_response": result["response_text"],

        "recommended_product": result["product_result"]["recommended_product"],
        "risk_level": result["safety_result"]["risk_level"],
        "escalation_required": result["safety_result"]["escalation_required"],

        "case_saved": saved_case["case_saved"],
        "case_id": saved_case["case_id"],
        "case_duplicate": saved_case["case_duplicate"],
        "case_save_reason": saved_case["reason"],

        "customer_profile": result["customer_profile"],
        "updated_customer_profile": result["updated_customer_profile"],
        "profile_updated": True,
        "profile_update_reason": "Customer profile updated",

        "detected_crop": result["product_result"]["detected_crop"],
        "detected_issue": result["product_result"]["detected_issue"],
        "product_reason": result["product_result"]["reason"],

        "rag": result["rag_result"],
        "order": result["order_result"],

        "langsmith_logged": result.get(
        "langsmith_logged",False)
    }
