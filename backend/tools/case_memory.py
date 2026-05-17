from datetime import datetime, timedelta

from backend.database.db import SessionLocal, engine, Base
from backend.database.models import Case


def init_database():
    """
    Creates database tables if they do not already exist.
    """
    Base.metadata.create_all(bind=engine)


def find_recent_duplicate_case(db, customer_id: str, message: str, minutes: int = 2):
    """
    Checks if the same customer sent the exact same message recently.
    If yes, reuse the existing case instead of creating duplicates.
    """

    time_limit = datetime.utcnow() - timedelta(minutes=minutes)

    duplicate_case = (
        db.query(Case)
        .filter(Case.customer_id == customer_id)
        .filter(Case.message == message)
        .filter(Case.created_at >= time_limit)
        .order_by(Case.created_at.desc())
        .first()
    )

    return duplicate_case


def save_case(
    customer_id: str,
    intent: str,
    message: str,
    possible_issue: str | None,
    recommended_product: str | None,
    risk_level: str,
    escalation_required: bool,
    order_id: str | None = None,
    order_status: str | None = None,
) -> dict:
    """
    Saves a support case into SQLite.
    If the same customer sends the same message within 2 minutes,
    it returns the existing case instead of creating a duplicate.
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
            intent=intent,
            message=message,
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
            "reason": "Case saved successfully."
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