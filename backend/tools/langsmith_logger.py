from langsmith import Client
from datetime import datetime
import os

client = Client()


def log_important_case(
    customer_id,
    message,
    intent,
    risk_level,
    escalation_required,
    payload=None
):

    try:

        client.create_run(
            name="agro_mind_important_case",
            run_type="chain",

            inputs={
                "customer_id": customer_id,
                "message": message,
                "intent": intent,
                "risk_level": risk_level,
                "escalation_required": escalation_required,
                "timestamp": str(datetime.utcnow())
            },

            outputs={
                "case_logged": True,
                "payload": payload or {}
            }
        )

        return True


    except Exception as e:
        print("LangSmith error:", e)
        return False
