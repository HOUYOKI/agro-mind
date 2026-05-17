from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.tools.intent_classifier import classify_intent
from backend.tools.safety_checker import check_safety
from backend.tools.product_recommender import recommend_product
from backend.tools.logistics_lookup import lookup_order
from backend.tools.case_memory import init_database, save_case

app = FastAPI(
    title="Agro-Mind API",
    description="AI-powered agricultural support assistant backend",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    customer_id: str
    message: str


@app.on_event("startup")
def startup_event():
    init_database()


@app.get("/")
def home():
    return {
        "message": "Agro-Mind backend is running",
        "status": "ok"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    intent = classify_intent(request.message)
    safety_result = check_safety(request.message, intent)

    product_result = {
        "recommended_product": None,
        "reason": "Product recommendation not needed for this intent.",
        "safety_note": None,
        "detected_crop": None,
        "detected_issue": None
    }

    order_result = {
        "order_found": False,
        "order_id": None,
        "status": None,
        "eta": None,
        "tracking_number": None,
        "reason": "Order lookup not needed for this intent."
    }

    if intent in ["crop_diagnosis", "product_question"]:
        product_result = recommend_product(request.message)

    if intent == "order_status":
        order_result = lookup_order(request.message, request.customer_id)

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

    saved_case = save_case(
        customer_id=request.customer_id,
        intent=intent,
        message=request.message,
        possible_issue=product_result["detected_issue"],
        recommended_product=product_result["recommended_product"],
        risk_level=safety_result["risk_level"],
        escalation_required=safety_result["escalation_required"],
        order_id=order_result["order_id"],
        order_status=order_result["status"],
    )

    return {
        "customer_id": request.customer_id,
        "received_message": request.message,
        "intent": intent,
        "response": response_text,
        "recommended_product": product_result["recommended_product"],
        "risk_level": safety_result["risk_level"],
        "escalation_required": safety_result["escalation_required"],
        "case_saved": saved_case["case_saved"],
        "case_id": saved_case["case_id"],
        "case_duplicate": saved_case["case_duplicate"],
        "case_save_reason": saved_case["reason"],
        "detected_crop": product_result["detected_crop"],
        "detected_issue": product_result["detected_issue"],
        "product_reason": product_result["reason"],
        "order": order_result
    }