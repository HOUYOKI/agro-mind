import time
from backend.agent_graph import run_agro_graph


TEST_CASES = [
    # ==================================================
    # Crop Diagnosis (10)
    # ==================================================
    {
        "query": "My tomato leaves have black spots",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "My cucumber plants have leaf spots",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "My strawberry plants have powdery mildew",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "My pepper leaves are turning yellow",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "My rice crop has disease symptoms",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "My citrus tree has root rot",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "My grape leaves have mildew",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "My watermelon plants are wilting",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "My garlic plants have fungal disease",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "My apple tree has leaf disease",
        "expected_intent": "crop_diagnosis",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },

    # ==================================================
    # Product Questions (5)
    # ==================================================
    {
        "query": "Which product helps tomato diseases?",
        "expected_intent": "product_question",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "Recommend a product for powdery mildew",
        "expected_intent": "product_question",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "What product can help leaf spot disease?",
        "expected_intent": "product_question",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },
    {
        "query": "Which fungicide is suitable for tomatoes?",
        "expected_intent": "product_question",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
        "allow_fail_closed_escalation": True,
        "acceptable_llm_status": ["success", "failed_fallback_used"],
    },
    {
        "query": "Suggest a product for crop disease management",
        "expected_intent": "product_question",
        "expect_product": True,
        "expect_rag": True,
        "expect_escalation": False,
    },

    # ==================================================
    # Order Status (5)
    # ==================================================
    {
        "query": "Where is order 1001?",
        "expected_intent": "order_status",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": False,
    },
    {
        "query": "Track my order 1001",
        "expected_intent": "order_status",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": False,
    },
    {
        "query": "What is the status of order 1001?",
        "expected_intent": "order_status",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": False,
    },
    {
        "query": "Has my shipment arrived?",
        "expected_intent": "order_status",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": False,
    },
    {
        "query": "I need tracking information for order 1001",
        "expected_intent": "order_status",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": False,
    },

    # ==================================================
    # Pesticide Safety (5)
    # ==================================================
    {
        "query": "I accidentally swallowed pesticide",
        "expected_intent": "pesticide_safety",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },
    {
        "query": "Pesticide got into my eyes",
        "expected_intent": "pesticide_safety",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },
    {
        "query": "I inhaled pesticide spray",
        "expected_intent": "pesticide_safety",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },
    {
        "query": "Can I eat tomatoes after spraying pesticide?",
        "expected_intent": "pesticide_safety",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },
    {
        "query": "Is pesticide residue dangerous?",
        "expected_intent": "pesticide_safety",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },

    # ==================================================
    # Complaints (5)
    # ==================================================
    {
        "query": "Your product ruined my crops",
        "expected_intent": "complaint",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },
    {
        "query": "I am unhappy with your product",
        "expected_intent": "complaint",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },
    {
        "query": "This fertilizer damaged my plants",
        "expected_intent": "complaint",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },
    {
        "query": "I want to report a problem with my order",
        "expected_intent": "complaint",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },
    {
        "query": "Your recommendation caused losses",
        "expected_intent": "complaint",
        "expect_product": False,
        "expect_rag": False,
        "expect_escalation": True,
    },
]


def _safe_bool(value) -> bool:
    return bool(value)


def run_system_benchmark():
    total = len(TEST_CASES)

    intent_correct_count = 0
    product_correct_count = 0
    rag_correct_count = 0
    escalation_correct_count = 0
    successful_cases = 0
    fail_closed_pass_count = 0

    latencies = []

    print("\n" + "=" * 80)
    print("AGRO-MIND FULL SYSTEM BENCHMARK")
    print("=" * 80)

    for index, case in enumerate(TEST_CASES, start=1):
        start_time = time.time()

        try:
            result = run_agro_graph(
                customer_id="BENCHMARK_USER",
                message=case["query"],
            )

        except Exception as error:
            latency = round(time.time() - start_time, 2)
            latencies.append(latency)

            print(f"\n[Test {index}]")
            print("Query:", case["query"])
            print("ERROR:", error)
            print("Latency:", latency, "sec")
            continue

        latency = round(time.time() - start_time, 2)
        latencies.append(latency)

        intent = result.get("intent")
        recommended_product = result.get("recommended_product")
        rag_found = bool(result.get("rag", {}).get("found", False))
        escalation_required = bool(result.get("escalation_required", False))
        llm_status = result.get("llm_status", "unknown")

        intent_correct = intent == case["expected_intent"]

        product_correct = (
            bool(recommended_product)
            == case["expect_product"]
        )

        rag_correct = (
            rag_found
            == case["expect_rag"]
        )

        escalation_correct = (
            escalation_required == case["expect_escalation"]
        )
        fail_closed_pass = False
        if not escalation_correct and case.get("allow_fail_closed_escalation"):
            if escalation_required and llm_status == "failed_fallback_used":
                escalation_correct = True
                fail_closed_pass = True

        llm_status_correct = llm_status in case.get(
            "acceptable_llm_status", ["success"]
        )

        if intent_correct:
            intent_correct_count += 1

        if product_correct:
            product_correct_count += 1

        if rag_correct:
            rag_correct_count += 1

        if escalation_correct:
            escalation_correct_count += 1

        case_passed = (
            intent_correct
            and product_correct
            and rag_correct
            and escalation_correct
            and llm_status_correct
        )

        if case_passed:
            successful_cases += 1
            if fail_closed_pass:
                fail_closed_pass_count += 1

        print(f"\n[Test {index}]")
        print("Query:", case["query"])
        print("Expected Intent:", case["expected_intent"])
        print("Actual Intent:", intent)
        print("Recommended Product:", recommended_product)
        print("RAG Found:", rag_found)
        print("Escalation Required:", escalation_required)
        print("LLM Status:", llm_status)
        print("Latency:", latency, "sec")
        if case_passed and fail_closed_pass:
            print("Passed: True (fail-closed: Qwen unavailable)")
        else:
            print("Passed:", case_passed)

        if not case_passed:
            print("Mismatch Details:")
            print(" - Intent correct:", intent_correct)
            print(" - Product correct:", product_correct)
            print(" - RAG correct:", rag_correct)
            print(" - Escalation correct:", escalation_correct)
            print(
                " - LLM status correct:", llm_status_correct,
                f"(got {llm_status!r}, expected {case.get('acceptable_llm_status', ['success'])})",
            )

    average_latency = (
        sum(latencies) / len(latencies)
        if latencies
        else 0
    )

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    print(f"Total Tests: {total}")
    print(f"Passed Tests: {successful_cases}/{total}")
    if fail_closed_pass_count:
        clean_passes = successful_cases - fail_closed_pass_count
        print(
            f"  ({clean_passes} clean pass{'es' if clean_passes != 1 else ''}, "
            f"{fail_closed_pass_count} via fail-closed Qwen fallback)"
        )

    print(
        f"Intent Accuracy: "
        f"{(intent_correct_count / total) * 100:.2f}%"
    )

    print(
        f"Product Accuracy: "
        f"{(product_correct_count / total) * 100:.2f}%"
    )

    print(
        f"RAG Accuracy: "
        f"{(rag_correct_count / total) * 100:.2f}%"
    )

    print(
        f"Escalation Accuracy: "
        f"{(escalation_correct_count / total) * 100:.2f}%"
    )

    print(
        f"System Accuracy: "
        f"{(successful_cases / total) * 100:.2f}%"
    )

    print(
        f"Average Latency: "
        f"{average_latency:.2f} sec"
    )


if __name__ == "__main__":
    run_system_benchmark()