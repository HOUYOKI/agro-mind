import json

from backend.agent_graph import run_agro_graph

result = run_agro_graph(
    customer_id="123",
    message="I accidentally swallowed pesticide"
)

print(json.dumps(result, indent=2, ensure_ascii=False))