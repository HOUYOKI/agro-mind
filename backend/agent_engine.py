import os
import sys
import json

# Setup system paths for backend tools resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.join(current_dir, "tools")
if tools_dir not in sys.path:
    sys.path.append(tools_dir)

# Import original core utilities and modules
from tools.safety_checker import check_safety
from tools.intent_classifier import classify_intent
from tools.product_recommender import recommend_product
from tools.logistics_lookup import lookup_order

# Import newly integrated multi-agent pipeline components
from tools.human_escalation import escalate_case
from tools.conversation_summary import summarize_conversation
from tools.case_memory import save_case, init_database


def format_agent_output(response) -> None:
    """Formats and prints the pipeline outputs into structured console dashboards."""
    print("\n🤖 AI Agent Response:")
    if isinstance(response, dict):
        # Format layout for safety alerts triggered by human escalation logic
        if response.get("status") == "ESCALATION_TRIGGERED":
            print("==================================================")
            print("🚨 CRITICAL ESCALATION: HUMAN AGENT REQUIRED")
            print("==================================================")
            print(f"⚠️ RISK LEVEL : {response.get('risk_level', '').upper()}")
            print(f"📁 CATEGORY   : {response.get('category', '').upper()}")
            print(f"\n📋 ESCALATION MESSAGE:\n\"{response.get('reason', '')}\"")
            print("==================================================")
            
        # Format layout for shipping and logistics tracking data
        elif "order_found" in response or response.get("order_id") == "Detected":
            print("==================================================")
            print("📦 AGRO-MIND LOGISTICS & SHIPPING REPORT")
            print("==================================================")
            print(f"🆔 ORDER ID         : {response.get('order_id')}")
            print(f"🚦 STATUS           : {response.get('status')}")
            print(f"📅 ESTIMATED ARRIVAL: {response.get('eta')}")
            print(f"🔢 TRACKING NUMBER  : {response.get('tracking_number')}")
            print("\n📋 DETAILED SHIPPING DETAILS & STATUS:")
            print(f"\"{response.get('reason', '')}\"")
            print("==================================================")
            
        # Format layout for RAG agronomic diagnosis data
        else:
            print("==================================================")
            print("🌱 AGRO-MIND PROFESSIONAL DIAGNOSIS REPORT")
            print("==================================================")
            print(f"📦 RECOMMENDED PRODUCT : {str(response.get('recommended_product', '')).upper()}")
            print(f"🌾 TARGET CROP         : {response.get('detected_crop', 'N/A')}")
            print(f"🛑 IDENTIFIED PATHOLOGY: {response.get('detected_issue', 'N/A')}")
            print("\n📋 AGRONOMIC JUSTIFICATION & TREATMENT PLAN:")
            print(f"\"{response.get('reason', '')}\"")
            print("\n🛡️ CRITICAL SAFETY PROTOCOL:")
            print(response.get('safety_note', ''))
            print("==================================================")
    else:
        print(response)
        print("-" * 50)


def run_agricultural_agent(user_query: str):
    """Orchestrates the lifecycle execution of all 7 domain-specific tools."""
    
    # Step 1: Execute immediate context validation through Safety Checker
    print(f"\n🔍 [1/5] Checking query safety...")
    try:
        safety_result = check_safety(user_query, "general")
        
        # Intercept critical toxicity levels to trigger the Human Escalation engine
        if safety_result.get("escalation_required") or safety_result.get("risk_level") == "critical":
            print("🚨 High risk detected! Triggering Human Escalation Tool...")
            escalation_res = escalate_case(user_query, customer_id="farmer_123", intent="safety_violation")
            return escalation_res
            
    except Exception as e:
        return f"⚠️ Safety Module Error: {str(e)}"

    # Step 2: Route intent evaluation using the Intent Classifier
    print(f"🧠 [2/5] Analyzing user intent...")
    intent = classify_intent(user_query)
    print(f"💡 Detected Intent: {intent}")

    # Step 3: Extract semantics into text summaries via Qwen2.5
    print(f"📝 [3/5] Summarizing interaction brief...")
    summary_res = summarize_conversation(f"User Query: {user_query}")
    
    response = None
    
    # Step 4: Map user intents into dedicated agronomic processing tasks
    print(f"🌾 [4/5] Executing core function logic...")
    valid_rag_intents = ["crop_diagnosis", "product_question", "pesticide_safety", "disease", "pest", "symptom"]
    
    if intent in valid_rag_intents:
        try:
            response = recommend_product(user_query)
        except Exception as e:
            response = {
                "recommended_product": "Execution Halt",
                "reason": f"Orchestrator failed to parse recommendation engine. Details: {str(e)}",
                "safety_note": "Please review core tools integrity.",
                "detected_crop": "Pipeline Error",
                "detected_issue": "Pipeline Error"
            }
    
    elif intent == "order_status":
        try:
            response = lookup_order(user_query=user_query, customer_id="123")
            return response
        except Exception as e:
            return f"⚠️ Logistics Module Error: {str(e)}"
    
    else:
        response = "🌱 Welcome to Agro-Mind! How can I assist you with your crops, pests, or agricultural product questions today?"

    # Step 5: Persist runtime sessions and summaries locally inside SQLite storage
    print(f"💾 [5/5] Archiving case session into SQLite Memory...")
    try:
        order_id = response.get("order_id") if isinstance(response, dict) else None
        order_status = response.get("status") if isinstance(response, dict) else None
        
        save_case(
            customer_id="farmer_123",
            message=summary_res.get("summary", user_query),
            order_id=order_id,
            order_status=order_status
        )
    except Exception as e:
        print(f"⚠️ Memory Storage Warning: {str(e)}")

    return response


if __name__ == "__main__":
    print("====================================")
    print("     Agro-Mind AI Agent Engine      ")
    print("====================================")
    
    # Initialize transactional database schema on engine boot
    try:
        init_database()
    except Exception as e:
        print(f"Database initialization backup skipped: {e}")
    
    # Start the standard execution shell loop
    while True:
        user_input = input("\nAsk a question (or type 'exit' to quit): ")
        if user_input.strip().lower() in ['exit', 'quit', 'close']:
            print("Shutting down the engine. Happy engineering!")
            break
            
        if not user_input.strip():
            continue
            
        agent_response = run_agricultural_agent(user_input)
        format_agent_output(agent_response)