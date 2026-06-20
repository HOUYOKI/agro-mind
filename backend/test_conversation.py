from backend.tools.conversation_summary import summarize_conversation
import json
import time

conversation = """
Farmer: I have an orange farm and the leaves are turning yellow.
Agro-Mind: It may be nitrogen deficiency.
Farmer: Can you recommend a fertilizer?
Agro-Mind: Apply a balanced citrus fertilizer.
"""

start = time.time()

result = summarize_conversation(conversation)

latency = time.time() - start

print(json.dumps(result, indent=2, ensure_ascii=False))
print(f"\nLatency: {latency:.2f} sec")