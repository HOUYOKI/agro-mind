"""
Standalone test for build_rule_based_response() fallback path.

Calls build_rule_based_response() directly with nested AgroState structure
for four scenarios and checks for debug label leaks in the returned string.

Run from the project root:
    python scripts/test_fallback_responses.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent_graph import build_rule_based_response

# ── Labels that must never appear in customer-facing text ────────────────────
DEBUG_LABELS = [
    "Intent:",
    "Risk level:",
    "Safety reason:",
    "Detected crop:",
    "Possible issue:",
    "Possible product:",
    "Product reason:",
    "Safety note:",
    "Order status:",
    "Lookup reason:",
    "risk_level",
    "safety_result",
    "product_result",
    "order_result",
    "escalation_required",
    "llm_status",
]

# ── Base state — safe defaults for every scenario ───────────────────────────
BASE = {
    "customer_id": "test-001",
    "message": "test message",
    "intent": "general_question",
    "raw_intent": "general_question",
    "safety_result": {
        "risk_level": "low",
        "reason": "Safe.",
        "escalation_required": False,
    },
    "product_result": {
        "recommended_product": None,
        "product_id": None,
        "reason": "No recommendation.",
        "safety_note": None,
        "detected_crop": None,
        "detected_issue": None,
        "confidence": 0.0,
        "status": "skipped",
    },
    "order_result": {
        "order_found": False,
        "order_id": None,
        "status": None,
        "eta": None,
        "tracking_number": None,
        "reason": "Order lookup not needed.",
    },
    "rag_result": {},
    "customer_profile_summary": "No profile.",
    "response_text": "",
    "ai_response": "",
    "llm_status": "not_started",
    "execution_trace": [],
}

SCENARIOS = [
    # ── 1. High risk ─────────────────────────────────────────────────────────
    (
        "HIGH RISK — poison/ingestion (expect emergency message, no product)",
        {
            **BASE,
            "message": "I accidentally swallowed pesticide",
            "intent": "pesticide_safety",
            "safety_result": {
                "risk_level": "high",
                "reason": "High-risk pesticide ingestion detected.",
                "escalation_required": True,
            },
        },
    ),
    # ── 2. Order status ───────────────────────────────────────────────────────
    (
        "ORDER STATUS — order found (expect prose with order ID and status)",
        {
            **BASE,
            "message": "Where is my order 1001?",
            "intent": "order_status",
            "order_result": {
                "order_found": True,
                "order_id": "1001",
                "status": "in transit",
                "eta": "2026-06-25",
                "tracking_number": "TRK-887766",
                "reason": "The item 'Citrus Fungicide X' is currently [in transit] at Riyadh Warehouse.",
            },
        },
    ),
    # ── 3. Crop diagnosis with product ────────────────────────────────────────
    (
        "CROP DIAGNOSIS — product recommended (expect product name + expert caveat)",
        {
            **BASE,
            "message": "My tomato leaves have black spots",
            "intent": "crop_diagnosis",
            "product_result": {
                "recommended_product": "Citrus Fungicide X",
                "product_id": "P-001",
                "reason": "Effective against early blight in tomatoes.",
                "safety_note": "Follow product label.",
                "detected_crop": ["tomato"],
                "detected_issue": ["early blight"],
                "confidence": 0.85,
                "status": "success",
            },
        },
    ),
    # ── 4. Generic fallback ───────────────────────────────────────────────────
    (
        "GENERIC FALLBACK — general_question, no product, no order",
        {
            **BASE,
            "message": "Hello, I have a general question about farming.",
            "intent": "general_question",
        },
    ),
]


def run_all():
    print("\nCalling build_rule_based_response() directly — no LLM involved.\n")
    passed = 0
    failed = 0

    for label, state in SCENARIOS:
        print("=" * 70)
        print(f"  {label}")
        print("=" * 70)

        response = build_rule_based_response(dict(state))

        print(f"\nresponse:\n  {response}\n")

        leaks = [lbl for lbl in DEBUG_LABELS if lbl in response]
        if leaks:
            print(f"  FAIL — debug labels leaked: {leaks}")
            failed += 1
        else:
            print("  PASS — no debug labels detected")
            passed += 1

        print()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(SCENARIOS)} scenarios")
    print("=" * 70)


if __name__ == "__main__":
    run_all()
