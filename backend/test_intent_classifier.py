from backend.tools.intent_classifier import classify_intent

tests = [
    "My tomato leaves have black spots",
    "What is the dosage for this fertilizer?",
    "I accidentally swallowed pesticide",
    "Where is my order?",
    "Your product damaged my crops",
    "Hello, how are you?"
]

print("=" * 60)
print("INTENT CLASSIFIER TEST")
print("=" * 60)

for query in tests:
    intent = classify_intent(query)

    print(f"\nQuery: {query}")
    print(f"Intent: {intent}")