from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os

from backend.tools.intent_classifier import classify_intent
from backend.tools.safety_checker import check_safety
from backend.tools.product_recommender import recommend_product
from backend.tools.logistics_lookup import lookup_order
from backend.tools.case_memory import init_database, save_case
from backend.tools.image_diagnosis import analyze_crop_image
from backend.tools.llm_agent import ask_agro_mind

# IMPORTANT: this is our new RAG V3 adapter, not the old local RAG file
from backend.tools.rag_retriever import retrieve_agronomy_knowledge

# Customer profile memory
from backend.tools.customer_profile import (
    get_customer_profile,
    update_customer_profile,
    summarize_customer_profile,
    load_customers,
)


app = FastAPI(
    title="Agro-Mind API",
    description="AI-powered agricultural support assistant backend",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
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
        "status": "ok",
    }


@app.get("/customers")
def get_customers():
    return load_customers()


# ==========================================
# IMAGE DIAGNOSIS ENDPOINT
# ==========================================
@app.post("/diagnose")
async def diagnose(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = analyze_crop_image(temp_file_path)
        return result

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# ==========================================
# CHAT ENDPOINT
# ==========================================
@app.post("/chat")
def chat(request: ChatRequest):
    # 1. Classify customer intent
    intent = classify_intent(request.message)

    # 1.5 Load customer profile memory
    customer_profile = get_customer_profile(request.customer_id)
    customer_profile_summary = summarize_customer_profile(request.customer_id)

    # 2. Check safety level
    safety_result = check_safety(request.message, intent)

    # 3. Default product result
    product_result = {
        "recommended_product": None,
        "reason": "Product recommendation not needed for this intent.",
        "safety_note": None,
        "detected_crop": None,
        "detected_issue": None,
    }

    # 4. Default order result
    order_result = {
        "order_found": False,
        "order_id": None,
        "status": None,
        "eta": None,
        "tracking_number": None,
        "reason": "Order lookup not needed for this intent.",
    }

    # 5. Default RAG result
    rag_result = {
        "rag_used": False,
        "found": False,
        "summary": "RAG retrieval not needed for this intent.",
        "sources": [],
        "confidence": 0.0,
        "status": "skipped",
    }

    # 6. Run product recommender only when useful and not escalation-heavy
    if (
        intent in ["crop_diagnosis", "product_question"]
        and not safety_result["escalation_required"]
    ):
        product_result = recommend_product(request.message)

    # 7. Run RAG only when useful and safe
    # Do not run RAG for complaints, pesticide exposure, or high-risk safety cases.
    if (
        intent in ["crop_diagnosis", "product_question", "general_question"]
        and not safety_result["escalation_required"]
    ):
        rag_result = retrieve_agronomy_knowledge(request.message, intent)

    # 8. Run logistics/order lookup only for order intent
    if intent == "order_status":
        order_result = lookup_order(request.message, request.customer_id)

    # ==========================================
    # OLD RULE-BASED RESPONSE / FALLBACK
    # ==========================================
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

    # ==========================================
    # QWEN LLM FINAL CUSTOMER RESPONSE
    # ==========================================
    llm_prompt = f"""
You are writing the final chatbot response for Agro-Mind.

Customer message:
{request.message}

Customer profile context:
{customer_profile_summary}

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
- Intent: {intent}

Safety checker:
- Risk level: {safety_result['risk_level']}
- Safety reason: {safety_result['reason']}
- Escalation required: {safety_result['escalation_required']}

Product recommender:
- Detected crop: {product_result['detected_crop']}
- Detected issue: {product_result['detected_issue']}
- Recommended product: {product_result['recommended_product']}
- Product reason: {product_result['reason']}
- Safety note: {product_result['safety_note']}

RAG retriever:
- RAG used: {rag_result['rag_used']}
- Knowledge found: {rag_result['found']}
- Knowledge summary: {rag_result['summary']}
- Sources: {rag_result['sources']}
- Confidence: {rag_result['confidence']}
- RAG status: {rag_result['status']}

Order lookup:
- Order found: {order_result['order_found']}
- Order ID: {order_result['order_id']}
- Status: {order_result['status']}
- ETA: {order_result['eta']}
- Tracking number: {order_result['tracking_number']}
- Order reason: {order_result['reason']}

Write the final customer-facing chatbot answer.

Rules:
1. Do not greet with "Dear", "Hello C001", or write like an email.
2. Do not end with "Best regards" or "Agro-Mind Team".
3. Do not mention internal words like "intent", "tool result", "risk_level", "RAG", "debug", "customer_segment", or "upsell_opportunity".
4. Do not invent anything not shown in the tool results.
5. If no exact product match exists, say that clearly.
6. If the recommended product is only a general support product, do not present it as a guaranteed solution.
7. If escalation_required is True, say that a human expert should review or confirm the case.
8. For pesticide, chemical, harvest, dosage, or food safety, NEVER give exact waiting periods, dosage numbers, safety guarantees, or "it is safe after X days" unless the tool results explicitly provide that exact information.
9. If the customer asks whether food can be eaten after spraying, say you cannot confirm safety from the message alone. Tell them to check the specific product label for the pre-harvest interval/waiting period and consult a human agricultural expert.
10. If retrieved knowledge is found, use it to support the answer, but do not pretend it is a final diagnosis.
11. If RAG status is "placeholder", do not mention that to the customer.
12. Keep the answer between 3 and 7 short sentences.
13. Sound like a helpful chatbot, not a formal email.
14. Never use preferred_language from the customer profile to decide the answer language.
15. The response language must follow the customer's current message.
16. If the current message is English, answer in English.
17. If the current message is Chinese, answer in Chinese.
18. If the current message is mixed or unclear, use the main language of the current message.
19. Do not mention language rules to the customer.
"""

    try:
        ai_response = ask_agro_mind(llm_prompt)
        llm_status = "completed"

    except Exception as error:
        print(f"LLM error: {error}")
        ai_response = response_text
        llm_status = "failed_fallback_used"

    # ==========================================
    # SAVE CASE TO DATABASE
    # ==========================================
    saved_case = save_case(
        customer_id=request.customer_id,
        message=request.message,
        order_id=order_result["order_id"],
        order_status=order_result["status"],
    )

    # ==========================================
    # UPDATE CUSTOMER PROFILE
    # ==========================================
    updated_customer_profile = update_customer_profile(
        request.customer_id,
        {
            "last_intent": intent,
            "last_message": request.message,
            "crop": product_result["detected_crop"],
            "possible_issue": product_result["detected_issue"],
            "recommended_product": product_result["recommended_product"],
            "risk_level": safety_result["risk_level"],
            "order_id": order_result["order_id"],
            "order_status": order_result["status"],
            "escalation_required": safety_result["escalation_required"],
        },
    )

    # ==========================================
    # EXECUTION TRACE
    # ==========================================
    execution_trace = [
        {
            "step": 1,
            "task": "Classify customer intent",
            "status": "completed",
            "result": intent,
        },
        {
            "step": 2,
            "task": "Load customer profile",
            "status": "completed" if customer_profile else "not_found",
            "result": (
                customer_profile.get("profile_summary")
                if customer_profile
                else "No existing customer profile found"
            ),
        },
        {
            "step": 3,
            "task": "Check safety risk",
            "status": "completed",
            "result": safety_result["risk_level"],
        },
        {
            "step": 4,
            "task": "Retrieve agronomy knowledge if needed",
            "status": "completed" if rag_result["rag_used"] else "skipped",
            "result": rag_result["summary"] if rag_result["found"] else "No RAG knowledge found",
        },
        {
            "step": 5,
            "task": "Run product recommendation if needed",
            "status": (
                "completed"
                if intent in ["crop_diagnosis", "product_question"]
                and not safety_result["escalation_required"]
                else "skipped"
            ),
            "result": product_result["recommended_product"],
        },
        {
            "step": 6,
            "task": "Run order lookup if needed",
            "status": "completed" if intent == "order_status" else "skipped",
            "result": order_result["status"],
        },
        {
            "step": 7,
            "task": "Generate final response with Qwen",
            "status": llm_status,
            "result": (
                "Final chatbot response generated"
                if llm_status == "completed"
                else "Fallback rule-based response used"
            ),
        },
        {
            "step": 8,
            "task": "Save support case",
            "status": "completed" if saved_case["case_saved"] else "skipped",
            "result": saved_case["reason"],
        },
        {
            "step": 9,
            "task": "Update customer profile",
            "status": "completed",
            "result": "Customer profile updated",
        },
    ]

    # ==========================================
    # FINAL API RESPONSE
    # ==========================================
    return {
        "customer_id": request.customer_id,
        "received_message": request.message,
        "intent": intent,

        # Main final response shown to customer
        "response": ai_response,

        # Shows the agent workflow steps
        "execution_trace": execution_trace,

        # Old rule-based response kept for debugging
        "debug_rule_based_response": response_text,

        "recommended_product": product_result["recommended_product"],
        "risk_level": safety_result["risk_level"],
        "escalation_required": safety_result["escalation_required"],

        "case_saved": saved_case["case_saved"],
        "case_id": saved_case["case_id"],
        "case_duplicate": saved_case["case_duplicate"],
        "case_save_reason": saved_case["reason"],

        # Customer profile memory
        "customer_profile": customer_profile,
        "updated_customer_profile": updated_customer_profile,
        "profile_updated": True,
        "profile_update_reason": "Customer profile updated",

        "detected_crop": product_result["detected_crop"],
        "detected_issue": product_result["detected_issue"],
        "product_reason": product_result["reason"],

        "rag": rag_result,
        "order": order_result,
    }