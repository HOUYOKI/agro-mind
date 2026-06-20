from backend.tools.customer_profile import (
    update_customer_profile,
    get_customer_profile,
    summarize_customer_profile
)

print("=" * 60)
print("CUSTOMER PROFILE TEST")
print("=" * 60)

customer_id = "TEST_CUSTOMER_001"

profile = update_customer_profile(
    customer_id=customer_id,
    update_data={
        "crop": "Tomato",
        "possible_issue": "Early Blight",
        "recommended_product": "Pyraclostrobin",
        "order_id": "ORD-1001"
    }
)

print("\nUpdated Profile:")
print(profile)

saved_profile = get_customer_profile(customer_id)

print("\nRetrieved Profile:")
print(saved_profile)

print("\nProfile Summary:")
print(summarize_customer_profile(customer_id))