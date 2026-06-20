"""
Standalone test for generate_response_node() fallback path.

Forces ask_agro_mind() to raise so _build_customer_fallback_response() runs,
then prints state["response"] for four scenarios and checks for debug label leaks.

Run from the project root:
    python scripts/test_fallback_responses.py
"""

import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent_graph import generate_response_node

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
    "risk_level": "low",
    "safety_reason": "Safe.",
    "escalation_required": False,
    "human_review_required": False,
    "rag_result": {},
    "product_result": {},
    "order_result": {},
    "customer_profile_summary": "No profile.",
    "response": "",
    "llm_status": "not_started",
    "recommended_product": None,
    "product_id": None,
    "product_reason": None,
    "product_confidence": None,
    "detected_crop": None,
    "detected_issue": None,
    "order_id": None,
    "order_status": None,
}

SCENARIOS = [
    # ── 1. High risk ─────────────────────────────────────────────────────────
    (
        "HIGH RISK — poison/ingestion (expect emergency message, no product)",
        {
            **BASE,
            "message": "I accidentally swallowed pesticide",
            "intent": "pesticide_safety",
            "risk_level": "high",
            "safety_reason": "High-risk pesticide ingestion detected.",
            "escalation_required": True,
            "human_review_required": True,
        },
    ),
    # ── 2. Order status ───────────────────────────────────────────────────────
    (
        "ORDER STATUS — order found (expect prose with order ID and status)",
        {
            **BASE,
            "message": "Where is my order 1001?",
            "intent": "order_status",
            "risk_level": "low",
            "order_id": "1001",
            "order_status": "in transit",
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
            "risk_level": "low",
            "recommended_product": "Citrus Fungicide X",
            "product_id": "P-001",
            "detected_crop": ["tomato"],
            "detected_issue": ["early blight"],
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
            "risk_level": "low",
        },
    ),
]


def run_all():
    print("\nForcing ask_agro_mind() to raise — testing fallback path only.\n")
    passed = 0
    failed = 0

    for label, state in SCENARIOS:
        print("=" * 70)
        print(f"  {label}")
        print("=" * 70)

        with patch(
            "backend.agent_graph.ask_agro_mind",
            side_effect=RuntimeError("LLM unavailable — forced for test"),
        ):
            result = generate_response_node(dict(state))

        response = result.get("response", "")
        llm_status = result.get("llm_status", "")

        print(f"llm_status : {llm_status}")
        print(f"\nresponse:\n  {response}\n")

        leaks = [lbl for lbl in DEBUG_LABELS if lbl in response]
        if leaks:
            print(f"  FAIL — debug labels leaked: {leaks}")
            failed += 1
        else:
            print("  PASS — no debug labels detected")

        print()

    print("=" * 70)
    print(f"Results: {passed + (len(SCENARIOS) - failed)} passed, {failed} failed out of {len(SCENARIOS)} scenarios")
    print("=" * 70)


if __name__ == "__main__":
    run_all()
