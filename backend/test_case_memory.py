from backend.tools.case_memory import  (
    init_database,
    save_case
)

init_database()

result = save_case(
    customer_id="TEST001",
    message="Tomato leaves have black spots",
    intent="disease_detection",
    possible_issue="Early Blight",
    recommended_product="Pyraclostrobin",
    risk_level="medium",
    escalation_required=False
)

print(result)