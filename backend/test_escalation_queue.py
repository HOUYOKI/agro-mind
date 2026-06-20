from backend.tools.escalation_queue import (
    create_escalation_case,
    list_escalations,
    mark_escalation_reviewed
)

print("=" * 60)
print("ESCALATION QUEUE TEST")
print("=" * 60)

case = create_escalation_case(
    customer_id="TEST001",
    case_type="disease",
    reason="Farmer requested human agronomist review",
    ai_response="Unable to confidently diagnose crop disease"
)

print("\nCreated Escalation:")
print(case)

pending = list_escalations()

print("\nPending Escalations:")
print(pending[:1])

reviewed = mark_escalation_reviewed(
    case["case_id"],
    reviewer_note="Reviewed by agronomist"
)

print("\nReviewed Escalation:")
print(reviewed)