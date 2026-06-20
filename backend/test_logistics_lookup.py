from backend.tools.logistics_lookup import (
    extract_order_id,
    lookup_order
)

print("=" * 60)
print("LOGISTICS LOOKUP TEST")
print("=" * 60)

queries = [
    "Where is order 1001?",
    "Track ORD001",
    "My shipment has not arrived"
]

for query in queries:
    print(f"\nQuery: {query}")
    print("Extracted Order ID:", extract_order_id(query))

print("\n" + "=" * 60)
print("SECURITY TEST (Wrong Customer)")
print("=" * 60)

result = lookup_order(
    message="Where is order 1001?",
    customer_id="CUST001"
)

print(result)

print("\n" + "=" * 60)
print("SUCCESS TEST (Correct Customer)")
print("=" * 60)

result = lookup_order(
    message="Where is order 1001?",
    customer_id="123"
)

print(result)