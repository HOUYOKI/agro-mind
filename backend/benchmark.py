from backend.agent_graph import run_agro_graph
import time

TEST_CASES = [
    {
        "query": "My tomato leaves have black spots",
        "expected_intent": "crop_diagnosis",
    },
    {
        "query": "Where is order 1001?",
        "expected_intent": "order_status",
    },
    {
        "query": "I accidentally swallowed pesticide",
        "expected_intent": "pesticide_safety",
    },
    {
        "query": "Your product ruined my crops",
        "expected_intent": "complaint",
    },
]

correct = 0
latencies = []

print("\n" + "=" * 80)
print("AGRO-MIND DETAILED BENCHMARK")
print("=" * 80)

for idx, test in enumerate(TEST_CASES, start=1):

    query = test["query"]

    print(f"\n[Test {idx}]")
    print(f"Query: {query}")

    start = time.perf_counter()

    result = run_agro_graph(
        customer_id="123",
        message=query
    )

    total_time = time.perf_counter() - start
    latencies.append(total_time)

    predicted = result.get("intent")

    if predicted == test["expected_intent"]:
        correct += 1

    print(f"Expected Intent : {test['expected_intent']}")
    print(f"Predicted Intent: {predicted}")
    print(f"Latency         : {total_time:.2f} sec")

    print("\nExecution Trace:")

    trace = result.get("execution_trace", [])

    for step in trace:
        print(
            f"  Step {step.get('step')} | "
            f"{step.get('task')} | "
            f"{step.get('status')}"
        )

    print("-" * 80)

accuracy = (correct / len(TEST_CASES)) * 100

print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)
print(f"Total Tests      : {len(TEST_CASES)}")
print(f"Correct Intents  : {correct}")
print(f"Intent Accuracy  : {accuracy:.2f}%")
print(f"Average Latency  : {sum(latencies)/len(latencies):.2f} sec")
print(f"Min Latency      : {min(latencies):.2f} sec")
print(f"Max Latency      : {max(latencies):.2f} sec")
print("=" * 80)