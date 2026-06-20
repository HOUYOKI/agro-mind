from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.database.db import SessionLocal, engine, Base
from backend.database.models import Case


def init_database():
    """
    Create database tables if they do not exist.
    """
    Base.metadata.create_all(bind=engine)


def find_recent_duplicate_case(db, customer_id: str, message: str, minutes: int = 2):
    """
    Prevent saving the exact same customer message repeatedly within a short window.
    """
    time_limit = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    return (
        db.query(Case)
        .filter(Case.customer_id == customer_id)
        .filter(Case.message == message)
        .filter(Case.created_at >= time_limit)
        .order_by(Case.created_at.desc())
        .first()
    )


def save_case(
    customer_id: str,
    message: str,
    intent: str = "unknown",
    possible_issue: Optional[str] = None,
    recommended_product: Optional[str] = None,
    risk_level: str = "low",
    escalation_required: bool = False,
    order_id: Optional[str] = None,
    order_status: Optional[str] = None,
) -> dict:
    """
    Save customer support case to SQLite.

    This version does not require OpenAI.
    It uses the results already produced by the Agro-Mind tools.
    """

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

        new_case = Case(
            customer_id=customer_id,
            message=message,
            intent=intent,
            possible_issue=possible_issue,
            recommended_product=recommended_product,
            risk_level=risk_level,
            escalation_required=escalation_required,
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
            "reason": "Case saved successfully using tool outputs."
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