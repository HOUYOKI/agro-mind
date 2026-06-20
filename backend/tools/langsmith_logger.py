from langsmith import Client
from datetime import datetime


client = Client()


def log_important_case(
    customer_id,
    message,
    intent,
    risk_level,
    escalation_required
):

    try:

        client.create_run(
            name="important_agro_case",
            run_type="chain",

            inputs={
                "customer_id": customer_id,
                "message": message,
                "intent": intent,
                "risk_level": risk_level,
                "escalation_required": escalation_required,
                "time": str(datetime.utcnow())
            },

            outputs={
                "logged": True
            }
        )

        return True


    except Exception as e:
        print("LangSmith error:", e)
        return False
