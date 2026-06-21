from backend.tools.safety_checker import check_safety

result = check_safety(
    "Can I eat tomatoes after spraying pesticide?",
    "pesticide_safety"
)

print(result)