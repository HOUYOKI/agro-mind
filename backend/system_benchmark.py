
import time
from backend.agent_graph import run_agro_graph

TEST_CASES = [

    # ==================================================
    # Crop Diagnosis (10)
    # ==================================================

    {"query":"My tomato leaves have black spots","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"My cucumber plants have leaf spots","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"My strawberry plants have powdery mildew","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"My pepper leaves are turning yellow","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"My rice crop has disease symptoms","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"My citrus tree has root rot","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"My grape leaves have mildew","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"My watermelon plants are wilting","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"My garlic plants have fungal disease","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"My apple tree has leaf disease","expected_intent":"crop_diagnosis","expect_product":True,"expect_rag":True,"expect_escalation":False},

    # ==================================================
    # Product Questions (5)
    # ==================================================

    {"query":"Which product helps tomato diseases?","expected_intent":"product_question","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"Recommend a product for powdery mildew","expected_intent":"product_question","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"What product can help leaf spot disease?","expected_intent":"product_question","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"Which fungicide is suitable for tomatoes?","expected_intent":"product_question","expect_product":True,"expect_rag":True,"expect_escalation":False},

    {"query":"Suggest a product for crop disease management","expected_intent":"product_question","expect_product":True,"expect_rag":True,"expect_escalation":False},

    # ==================================================
    # Order Status (5)
    # ==================================================

    {"query":"Where is order 1001?","expected_intent":"order_status","expect_product":False,"expect_rag":False,"expect_escalation":False},

    {"query":"Track my order 1001","expected_intent":"order_status","expect_product":False,"expect_rag":False,"expect_escalation":False},

    {"query":"What is the status of order 1001?","expected_intent":"order_status","expect_product":False,"expect_rag":False,"expect_escalation":False},

    {"query":"Has my shipment arrived?","expected_intent":"order_status","expect_product":False,"expect_rag":False,"expect_escalation":False},

    {"query":"I need tracking information for order 1001","expected_intent":"order_status","expect_product":False,"expect_rag":False,"expect_escalation":False},

    # ==================================================
    # Pesticide Safety (5)
    # ==================================================

    {"query":"I accidentally swallowed pesticide","expected_intent":"pesticide_safety","expect_product":False,"expect_rag":False,"expect_escalation":True},

    {"query":"Pesticide got into my eyes","expected_intent":"pesticide_safety","expect_product":False,"expect_rag":False,"expect_escalation":True},

    {"query":"I inhaled pesticide spray","expected_intent":"pesticide_safety","expect_product":False,"expect_rag":False,"expect_escalation":True},

    {"query":"Can I eat tomatoes after spraying pesticide?","expected_intent":"pesticide_safety","expect_product":False,"expect_rag":False,"expect_escalation":True},

    {"query":"Is pesticide residue dangerous?","expected_intent":"pesticide_safety","expect_product":False,"expect_rag":False,"expect_escalation":True},

    # ==================================================
    # Complaints (5)
    # ==================================================

    {"query":"Your product ruined my crops","expected_intent":"complaint","expect_product":False,"expect_rag":False,"expect_escalation":True},

    {"query":"I am unhappy with your product","expected_intent":"complaint","expect_product":False,"expect_rag":False,"expect_escalation":True},

    {"query":"This fertilizer damaged my plants","expected_intent":"complaint","expect_product":False,"expect_rag":False,"expect_escalation":True},

    {"query":"I want to report a problem with my order","expected_intent":"complaint","expect_product":False,"expect_rag":False,"expect_escalation":True},

    {"query":"Your recommendation caused losses","expected_intent":"complaint","expect_product":False,"expect_rag":False,"expect_escalation":True},
]


def run_system_benchmark():

    total = len(TEST_CASES)

    intent_correct_count = 0
    product_correct_count = 0
    rag_correct_count = 0
    escalation_correct_count = 0
    successful_cases = 0

    latencies = []

    print("\n" + "=" * 80)
    print("AGRO-MIND FULL SYSTEM BENCHMARK")
    print("=" * 80)

    for index, case in enumerate(TEST_CASES, start=1):

        start_time = time.time()

        result = run_agro_graph(
            customer_id="BENCHMARK_USER",
            message=case["query"]
        )

        latency = round(time.time() - start_time, 2)
        latencies.append(latency)

        intent_correct = (
            result["intent"] == case["expected_intent"]
        )

        product_correct = (
            bool(result["recommended_product"])
            == case["expect_product"]
        )

        rag_correct = (
            result["rag"]["found"]
            == case["expect_rag"]
        )

        escalation_correct = (
            result["escalation_required"]
            == case["expect_escalation"]
        )

        if intent_correct:
            intent_correct_count += 1

        if product_correct:
            product_correct_count += 1

        if rag_correct:
            rag_correct_count += 1

        if escalation_correct:
            escalation_correct_count += 1

        if (
            intent_correct
            and product_correct
            and rag_correct
            and escalation_correct
        ):
            successful_cases += 1

        print(f"\n[Test {index}]")
        print("Query:", case["query"])
        print("Intent:", result["intent"])
        print("Latency:", latency, "sec")

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    print(
        f"Intent Accuracy: {(intent_correct_count/total)*100:.2f}%"
    )

    print(
        f"Product Accuracy: {(product_correct_count/total)*100:.2f}%"
    )

    print(
        f"RAG Accuracy: {(rag_correct_count/total)*100:.2f}%"
    )

    print(
        f"Escalation Accuracy: {(escalation_correct_count/total)*100:.2f}%"
    )

    print(
        f"System Accuracy: {(successful_cases/total)*100:.2f}%"
    )

    print(
        f"Average Latency: {sum(latencies)/len(latencies):.2f} sec"
    )


if __name__ == "__main__":
    run_system_benchmark()