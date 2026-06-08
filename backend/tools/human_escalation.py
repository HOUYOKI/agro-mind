def escalate_case(customer_id, reason):
    return {
        "escalated": True,
        "assigned_to": "Human Agent",
        "reason": reason
    }