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
from backend.tools.rag_retriever import retrieve_agronomy_knowledge

from backend.database.db import SessionLocal
from backend.database.models import Case


app = FastAPI(
    title="Agro-Mind API",
    description="AI-powered agricultural support assistant backend",
    version="0.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175"
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
        "status": "ok"
    }


# ==========================================
# HUMAN ESCALATION QUEUE ENDPOINT
# ==========================================
@app.get("/cases/escalations")
def get_escalated_cases(limit: int = 20):
    """
    Human review queue.
    Shows cases that require human support/agronomy review.
    """
    db = SessionLocal()

    try:
        cases = (
            db.query(Case)
            .filter(Case.escalation_required.is_(True))
            .order_by(Case.created_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "count": len(cases),
            "cases": [
                {
                    "case_id": case.case_id,
                    "customer_id": case.customer_id,
                    "intent": case.intent,
                    "message": case.message,
                    "risk_level": case.risk_level,
                    "possible_issue": case.possible_issue,
                    "recommended_product": case.recommended_product,
                    "order_id": case.order_id,
                    "order_status": case.order_status,
                    "escalation_required": case.escalation_required,
                    "created_at": case.created_at.isoformat() if case.created_at else None
                }
                for case in cases
            ]
        }

    finally:
        db.close()


# ==========================================
# IMAGE DIAGNOSIS ENDPOINT
# ==========================================
@app.post("/diagnose")
async def diagnose(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = analyze_crop_image(temp_file_path, use_llm=False)
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

    # 2. Check safety level
    safety_result = check_safety(request.message, intent)

    # 3. Default product result
    product_result = {
        "recommended_product": None,
        "reason": "Product recommendation not needed for this intent.",
        "safety_note": None,
        "detected_crop": None,
        "detected_issue": None
    }

    # 4. Default order result
    order_result = {
        "order_found": False,
        "order_id": None,
        "status": None,
        "eta": None,
        "tracking_number": None,
        "reason": "Order lookup not needed for this intent."
    }

    # 5. Default RAG result
    rag_result = {
        "rag_used": False,
        "found": False,
        "summary": "RAG retrieval not needed for this intent.",
        "sources": [],
        "confidence": 0.0,
        "status": "skipped"
    }

    # ==========================================
    # COMPLAINT / HUMAN REVIEW OVERRIDE
    # ==========================================
    if intent == "complaint":
        if safety_result["risk_level"] == "low":
            safety_result["risk_level"] = "medium"

        safety_result["reason"] = "Customer complaint or crop damage claim requires human review."
        safety_result["escalation_required"] = True

    # ==========================================
    # TOOL ROUTING
    # ==========================================

    # Run product recommender only for normal product/crop support.
    # Do not recommend products for complaints or safety escalations.
    if intent in ["crop_diagnosis", "product_question"] and not safety_result["escalation_required"]:
        product_result = recommend_product(request.message)

    # Run RAG only for agronomy/product support.
    # Do not run RAG for complaints or generic pesticide exposure.
    if intent in ["crop_diagnosis", "product_question"] and not safety_result["escalation_required"]:
        rag_result = retrieve_agronomy_knowledge(request.message, intent)

    # Run logistics/order lookup only for order intent.
    # IMPORTANT: lookup_order expects (user_query, customer_id)
    if intent == "order_status":
        order_result = lookup_order(request.message, request.customer_id)

    # ==========================================
    # RULE-BASED RESPONSE / FALLBACK
    # ==========================================
    response_text = (
        f"Intent: {intent}\n\n"
        f"Risk level: {safety_result['risk_level']}\n"
        f"Safety reason: {safety_result['reason']}\n\n"
    )

    if intent == "complaint":
        response_text += (
            "This complaint should be reviewed by a human support or agronomy expert. "
            "Please provide the product name, order number, photos of the crop damage, "
            "when and how the product was applied, and any label instructions followed."
        )

    elif product_result["recommended_product"]:
        response_text += (
            f"Detected crop: {product_result['detected_crop']}\n"
            f"Possible issue: {product_result['detected_issue']}\n"
            f"Possible product: {product_result['recommended_product']}\n"
            f"Product reason: {product_result['reason']}\n"
            f"Safety note: {product_result['safety_note']}\n\n"
            "Important: Please confirm the diagnosis before applying any pesticide."
        )

    elif intent == "order_status":
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

    elif intent == "pesticide_safety":
        response_text += (
            "Pesticide or chemical exposure was detected. "
            "Follow the product label first-aid instructions, wash exposed skin with clean water, "
            "and seek medical or human expert review if symptoms continue or exposure is severe."
        )

    else:
        response_text += "No product recommendation was made for this message."

    # ==========================================
    # QWEN LLM FINAL CUSTOMER RESPONSE
    # ==========================================
    llm_prompt = f"""
You are writing the final chatbot response for Agro-Mind.

Customer message:
{request.message}

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
3. Do not mention internal words like "intent", "tool result", "risk_level", "RAG", or "debug".
4. Do not invent anything not shown in the tool results.
5. If no exact product match exists, say that clearly.
6. If the recommended product is only a general support product, do not present it as a guaranteed solution.
7. If escalation_required is True, say that a human expert should review or confirm the case.
8. For pesticide, chemical, harvest, dosage, or food safety, NEVER give exact waiting periods, dosage numbers, safety guarantees, or "it is safe after X days" unless the tool results explicitly provide that exact information.
9. If the customer asks whether food can be eaten after spraying, say you cannot confirm safety from the message alone. Tell them to check the specific product label for the pre-harvest interval/waiting period and consult a human agricultural expert.
10. If retrieved knowledge is found, use it to support the answer, but do not pretend it is a final diagnosis.
11. If RAG status is "placeholder", do not mention that to the customer.
12. If the intent is complaint, do not recommend any product. Apologize briefly, say the case should be reviewed by a human support/agronomy expert, and ask for product name, order number, photos, and application details.
13. If the customer reports pesticide or chemical exposure, give safe first-aid style guidance only. Do not recommend products. Do not downplay the risk. Tell them to follow the label and seek medical/human expert help if symptoms are serious or exposure involves eyes, breathing, ingestion, children, pets, or livestock.
14. Keep the answer between 3 and 7 short sentences.
15. Sound like a helpful chatbot, not a formal email.
"""

    try:
        ai_response = ask_agro_mind(llm_prompt)
        llm_status = "completed"
    except Exception as e:
        print(f"LLM error: {e}")
        ai_response = response_text
        llm_status = "failed_fallback_used"

    # ==========================================
    # SAVE CASE TO DATABASE
    # ==========================================
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

    # ==========================================
    # EXECUTION TRACE
    # ==========================================
    execution_trace = [
        {
            "step": 1,
            "task": "Classify customer intent",
            "status": "completed",
            "result": intent
        },
        {
            "step": 2,
            "task": "Check safety risk",
            "status": "completed",
            "result": safety_result["risk_level"]
        },
        {
            "step": 3,
            "task": "Retrieve agronomy knowledge if needed",
            "status": "completed" if rag_result["rag_used"] else "skipped",
            "result": rag_result["summary"] if rag_result["found"] else "No RAG knowledge found"
        },
        {
            "step": 4,
            "task": "Run product recommendation if needed",
            "status": "completed" if product_result["recommended_product"] else "skipped",
            "result": product_result["recommended_product"]
        },
        {
            "step": 5,
            "task": "Run order lookup if needed",
            "status": "completed" if intent == "order_status" else "skipped",
            "result": order_result["status"]
        },
        {
            "step": 6,
            "task": "Generate final response with Qwen",
            "status": llm_status,
            "result": "Final chatbot response generated" if llm_status == "completed" else "Fallback rule-based response used"
        },
        {
            "step": 7,
            "task": "Save support case",
            "status": "completed" if saved_case["case_saved"] else "skipped",
            "result": saved_case["reason"]
        }
    ]

    # ==========================================
    # FINAL API RESPONSE
    # ==========================================
    return {
        "customer_id": request.customer_id,
        "received_message": request.message,
        "intent": intent,

        "response": ai_response,
        "execution_trace": execution_trace,
        "debug_rule_based_response": response_text,

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

        "rag": rag_result,
        "order": order_result
    }