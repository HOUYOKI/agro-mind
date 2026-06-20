from backend.tools.human_escalation import escalate_case
import json
import time

print("=" * 60)
print("HUMAN ESCALATION TEST")
print("=" * 60)

tests = [
    {
        "query": "I accidentally swallowed some fertilizer and now I feel dizzy.",
        "intent": "pesticide_issue"
    },
    {
        "query": "My tomato leaves have black spots.",
        "intent": "disease_detection"
    },
    {
        "query": "I mixed two pesticides together and now my skin is burning.",
        "intent": "chemical_safety"
    }
]

for test in tests:

    start = time.time()

    result = escalate_case(
        user_query=test["query"],
        customer_id="TEST001",
        intent=test["intent"]
    )

    latency = time.time() - start

    print("\nQuery:")
    print(test["query"])

    print("\nResult:")
    print(json.dumps(result, indent=2))

    print(f"\nLatency: {latency:.2f} sec")
    print("-" * 60)