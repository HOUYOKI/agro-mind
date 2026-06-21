from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import tempfile

from backend.tools.case_memory import init_database
from backend.vision.diagnosis_tool import diagnose_crop_image
from backend.tools.customer_profile import load_customers, update_customer_profile
from backend.agent_graph import run_agro_graph
from backend.tools.escalation_queue import (
    create_escalation_case,
    list_escalations,
    mark_escalation_reviewed,
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


class EscalationRequest(BaseModel):
    customer_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    issue: str
    ai_response: Optional[str] = None
    source: Optional[str] = "manual"


class EscalationReviewRequest(BaseModel):
    reviewer_note: Optional[str] = None


def _is_chinese_text(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text or "")


def _is_poison_or_self_harm_message(text: str) -> bool:
    lowered = (text or "").lower()

    danger_phrases = [
        "eat poison",
        "eat poisonous",
        "eat poisoness",
        "consume poison",
        "drink poison",
        "i want to eat poison",
        "i want to eat poisonous",
        "i want to eat poisoness",
        "i want to drink poison",
        "poison myself",
        "harm myself",
        "kill myself",
        "suicide",
        "self harm",
        "self-harm",

        "吃毒药",
        "喝毒药",
        "想吃毒药",
        "想喝毒药",
        "服毒",
        "毒死自己",
        "伤害自己",
        "自杀",
        "自残",
    ]

    return any(phrase in lowered for phrase in danger_phrases)


def _safe_high_risk_response(message: str) -> str:
    if _is_chinese_text(message):
        return (
            "这可能涉及中毒、误食有害物质或自我伤害风险。请不要食用或接触该物质。"
            "请立即联系当地急救服务、毒物控制中心或医疗专业人员。"
            "如果与农药有关，请保留产品标签供专业人员查看。"
            "此案例已被标记为需要人工审核。"
        )

    return (
        "This may involve poison ingestion, chemical exposure, or self-harm risk. "
        "Do not consume or touch the substance. Please contact local emergency services, "
        "poison control, or a medical professional immediately. If this involves a pesticide, "
        "keep the product label available for the professional to review. "
        "This case has been flagged for human review."
    )


@app.on_event("startup")
def startup_event():
    init_database()


@app.get("/")
def home():
    return {
        "message": "Agro-Mind backend is running",
        "status": "ok",
        "workflow": "LangGraph",
    }


@app.get("/customers")
def get_customers():
    return load_customers()


@app.post("/human-escalation")
def human_escalation(request: EscalationRequest):
    case = create_escalation_case(
        customer_id=request.customer_id,
        case_type="manual_human_request",
        reason=request.issue,
        ai_response=request.ai_response or "",
        source=request.source or "manual",
        payload={
            "name": request.name,
            "phone": request.phone,
            "issue": request.issue,
        },
    )

    updated_profile = None

    try:
        updated_profile = update_customer_profile(
            request.customer_id,
            {
                "human_escalation_requested": True,
                "escalation_case_id": case["case_id"],
            },
        )
    except Exception as error:
        print("Customer profile escalation update failed:", error)

    return {
        "status": "received",
        "message": "Human agent will contact you.",
        "human_review_required": True,
        "escalation_required": True,
        "escalation_case_id": case["case_id"],
        "case": case,
        "updated_customer_profile": updated_profile,
    }


@app.get("/escalations")
def get_escalations(status: str = "pending"):
    return {
        "status": status,
        "items": list_escalations(status=status),
    }


@app.post("/escalations/{case_id}/review")
def review_escalation(case_id: str, request: EscalationReviewRequest):
    try:
        updated_case = mark_escalation_reviewed(
            case_id=case_id,
            reviewer_note=request.reviewer_note,
        )

        return {
            "success": True,
            "case": updated_case,
        }

    except ValueError as error:
        return {
            "success": False,
            "error": str(error),
        }


@app.post("/diagnose")
async def diagnose(
    file: UploadFile = File(...),
    customer_id: str = Form("unknown"),
):
    _MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
    temp_file_path = None

    data = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 10 MB limit.")

    try:
        suffix = os.path.splitext(file.filename or "")[1].lower() or ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_file_path = tmp.name
            tmp.write(data)

        result = diagnose_crop_image(temp_file_path)

        needs_review = bool(
            result.get("needs_human_review")
            or result.get("human_review_required")
            or result.get("escalation_required")
        )

        if needs_review and not result.get("escalation_case_id"):
            ai_response = (
                result.get("response")
                or result.get("customer_response")
                or result.get("safe_response")
                or "This image diagnosis requires review by a human agronomist."
            )

            reason = (
                result.get("reason")
                or result.get("diagnosis")
                or result.get("disease")
                or "Low-confidence image diagnosis requires agronomist review."
            )

            case = create_escalation_case(
                customer_id=customer_id,
                case_type="image_diagnosis",
                reason=reason,
                ai_response=ai_response,
                source="diagnose",
                payload=result,
            )

            result["human_review_required"] = True
            result["escalation_required"] = True
            result["escalation_case_id"] = case["case_id"]

            try:
                updated_profile = update_customer_profile(
                    customer_id,
                    {
                        "human_escalation_requested": True,
                        "escalation_case_id": case["case_id"],
                    },
                )
                result["updated_customer_profile"] = updated_profile

            except Exception as error:
                print("Customer profile image escalation update failed:", error)

        return result

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.post("/chat")
def chat(request: ChatRequest):
    result = run_agro_graph(
        customer_id=request.customer_id,
        message=request.message,
    )
    
    # Final safety cleanup:
    # If the graph produced a generic crop/food-safety response for a poison/self-harm message,
    # override it with a safer emergency-style response.
    if result.get("risk_level") == "high" and _is_poison_or_self_harm_message(request.message):
        result["response"] = _safe_high_risk_response(request.message)
        result["recommended_product"] = None
        result["detected_crop"] = None
        result["detected_issue"] = "High-risk poison or self-harm message"
        result["product_reason"] = "High-risk safety case. Product recommendation disabled."
        result["escalation_required"] = True
        result["human_review_required"] = True

    needs_review = bool(
        result.get("escalation_required")
        or result.get("human_review_required")
        or result.get("risk_level") == "high"
    )

    if needs_review and not result.get("escalation_case_id"):
        ai_response = (
            result.get("response")
            or result.get("answer")
            or "This case requires human review."
        )

        reason = (
            result.get("safety_reason")
            or result.get("risk_reason")
            or result.get("reason")
            or result.get("detected_issue")
            or result.get("product_reason")
            or "Text case requires human support review."
        )

        case = create_escalation_case(
            customer_id=request.customer_id,
            case_type=result.get("intent") or "chat_support",
            reason=reason,
            ai_response=ai_response,
            source="chat",
            payload=result,
        )

        result["human_review_required"] = True
        result["escalation_required"] = True
        result["escalation_case_id"] = case["case_id"]

        try:
            updated_profile = update_customer_profile(
                request.customer_id,
                {
                    "human_escalation_requested": True,
                    "escalation_case_id": case["case_id"],
                },
            )

            result["updated_customer_profile"] = updated_profile
            result["customer_profile"] = updated_profile

        except Exception as error:
            print("Customer profile chat escalation update failed:", error)

    

    return result
