from datetime import datetime, timedelta, timezone
import os
import json
from typing import Optional
from pydantic import BaseModel, Field
from openai import OpenAI

# Updated imports to include backend path
from backend.database.db import SessionLocal, engine, Base
from backend.database.models import Case

client = OpenAI()

class CaseAnalysis(BaseModel):
    intent: str = Field(description="The primary intent of the customer (e.g., refund, shipping_query, technical_issue).")
    possible_issue: Optional[str] = Field(default=None, description="Brief description of the issue if present, otherwise null.")
    recommended_product: Optional[str] = Field(default=None, description="Any product recommendation relevant to the query, if applicable.")
    risk_level: str = Field(description="Risk level of the message: low, medium, or high.")
    escalation_required: bool = Field(description="True if the message implies urgent human intervention, severe anger, or legal threats.")


def init_database():
    Base.metadata.create_all(bind=engine)


def find_recent_duplicate_case(db, customer_id: str, message: str, minutes: int = 2):
    time_limit = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    duplicate_case = (
        db.query(Case)
        .filter(Case.customer_id == customer_id)
        .filter(Case.message == message)
        .filter(Case.created_at >= time_limit)
        .order_by(Case.created_at.desc())
        .first()
    )

    return duplicate_case


def analyze_message_with_llm(message: str) -> CaseAnalysis:
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI support triage assistant. Analyze the incoming customer message and extract the metadata precisely."
                },
                {"role": "user", "content": message},
            ],
            response_format=CaseAnalysis,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        return CaseAnalysis(
            intent="unknown",
            possible_issue=f"LLM analysis failed: {str(e)}",
            recommended_product=None,
            risk_level="low",
            escalation_required=False
        )


def save_case(
    customer_id: str,
    message: str,
    order_id: Optional[str] = None,
    order_status: Optional[str] = None,
) -> dict:
    db = SessionLocal()

    try:
        duplicate_case = find_recent_duplicate_case(
            db=db,
            customer_id=customer_id,
            message=message,
            minutes=2
        )

        if duplicate_case:
            return {
                "case_saved": True,
                "case_id": duplicate_case.case_id,
                "case_duplicate": True,
                "reason": "Duplicate message detected. Reused recent case instead of creating a new one."
            }

        analysis = analyze_message_with_llm(message)

        new_case = Case(
            customer_id=customer_id,
            message=message,
            intent=analysis.intent,
            possible_issue=analysis.possible_issue,
            recommended_product=analysis.recommended_product,
            risk_level=analysis.risk_level,
            escalation_required=analysis.escalation_required,
            order_id=order_id,
            order_status=order_status,
        )

        db.add(new_case)
        db.commit()
        db.refresh(new_case)

        return {
            "case_saved": True,
            "case_id": new_case.case_id,
            "case_duplicate": False,
            "reason": "Case analyzed by LLM and saved successfully."
        }

    except Exception as error:
        db.rollback()
        return {
            "case_saved": False,
            "case_id": None,
            "case_duplicate": False,
            "reason": f"Failed to save case: {str(error)}"
        }

    finally:
        db.close()


if __name__ == '__main__':
    print("\n==================================================")
    print("   Running Case Memory & DB Storage Check...")
    print("==================================================")
    
    init_database()
    
    sample_message = "I need to check the delivery status of my organic fertilizer order."
    print(f'Processing Sample Message: "{sample_message}"')
    
    result = save_case(
        customer_id="farmer_101",
        message=sample_message,
        order_id="ORD-9921",
        order_status="pending"
    )
    
    print("\nDatabase Saving Output:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("==================================================\n")