import traceback
import json

from backend.tools.safety_checker import check_safety
from backend.tools.product_recommender import recommend_product
from backend.tools.logistics_lookup import lookup_order
from backend.tools.intent_classifier import classify_intent
from backend.tools.human_escalation import escalate_case
from backend.tools.conversation_summary import summarize_conversation
from backend.tools.case_memory import save_case, init_database


def test_all_agro_mind_tools():
    print("\n==================================================")
    print("      Agro-Mind Full Pipeline Validation Test      ")
    print("==================================================")
    
    try:
        print("\n[Setup] Initializing Database Jars...")
        init_database()
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")

    tasks = [
        ("Intent Classifier", lambda: classify_intent("Where is my order?")),
        
        ("Safety Checker", lambda: check_safety("pesticide", intent="safety_check")),
        
        # قمنا بتعطيل هذه الأداة مؤقتاً هنا لحماية بقية الـ Pipeline من تعليق ChromaDB/Ollama
        # ("Product Recommender", lambda: recommend_product("How to use for citrus?")),
        
        ("Logistics Lookup", lambda: lookup_order(user_query="Where is my order?", customer_id="12345")),
        
        ("Human Escalation (Safety Agent)", lambda: escalate_case(
            user_query="I accidentally swallowed some fertilizer and now I feel dizzy.",
            customer_id="farmer_789",
            intent="pesticide_issue"
        )),
        
        ("Conversation Summary (Qwen2.5)", lambda: summarize_conversation(
            "Farmer: I have an orange farm and the leaves are turning yellow. I need a good fertilizer."
        )),
        
        ("Case Memory & DB Storage", lambda: save_case(
            customer_id="farmer_101",
            message="I need to check the delivery status of my organic fertilizer order.",
            order_id="ORD-9921",
            order_status="pending"
        ))
    ]
    
    for name, func in tasks:
        print(f"\n⚙️ Testing Tool: {name}...")
        try:
            result = func()
            print(f"✅ {name} works beautifully!")
            if isinstance(result, dict):
                print(json.dumps(result, indent=2, ensure_ascii=False)[:300] + "...\n(Truncated for preview)")
            else:
                print(f"Result Preview: {result}\n")
        except Exception:
            print(f"❌ Error detected in tool: {name}")
            traceback.print_exc()
            print("-" * 40)

    print("\n==================================================")
    print("         End of Comprehensive Tool Test           ")
    print("==================================================\n")


if __name__ == "__main__":
    test_all_agro_mind_tools()