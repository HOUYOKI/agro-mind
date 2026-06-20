from backend.tools.llm_agent import ask_agro_mind

response = ask_agro_mind(
    """
Farmer question:
My tomato leaves have black spots.

Tool Results:
Recommended Product: Pyraclostrobin (Kairun)
Disease: Early Blight
Safety Note: Follow the official product label.
"""
)

print(response)