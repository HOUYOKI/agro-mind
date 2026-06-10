import traceback
from backend.tools.safety_checker import check_safety
from backend.tools.product_recommender import recommend_product
from backend.tools.logistics_lookup import lookup_order
from backend.tools.intent_classifier import classify_intent

def test_my_tools():
    print("--- Starting Tool Validation Test ---")
    
    # We will test each tool one by one to isolate the error
    tasks = [
        ("Safety Checker", lambda: check_safety("pesticide", intent="safety_check")),
        ("Product Recommender", lambda: recommend_product("How to use for citrus?")),
        ("Logistics Lookup", lambda: lookup_order(user_query="Where is my order?", customer_id="12345")),
        ("Intent Classifier", lambda: classify_intent("Where is my order?"))
    ]
    
    for name, func in tasks:
        try:
            print(f"\nTesting: {name}...")
            result = func()
            print(f"✅ {name} works! Result: {result}")
        except Exception:
            print(f"❌ Error detected in: {name}")
            # This will show the exact file and line number causing the problem
            traceback.print_exc()

if __name__ == "__main__":
    test_my_tools()