from backend.tools.safety_checker import check_safety

tests = [
    ("I accidentally swallowed pesticide", "pesticide_safety"),
    ("Pesticide got into my eyes", "pesticide_safety"),
    ("Can I eat tomatoes one day after spraying?", "product_question"),
    ("Your product ruined my crops", "complaint"),
    ("My tomato leaves have black spots", "crop_diagnosis"),
    ("Hello, how are you?", "general_question")
]

print("=" * 60)
print("SAFETY CHECKER TEST")
print("=" * 60)

for query, intent in tests:
    result = check_safety(query, intent)

    print(f"\nQuery: {query}")
    print(result)