import ollama


MODEL_NAME = "qwen2.5:7b-instruct"


def ask_agro_mind(user_message: str) -> str:
    """
    Sends a prepared prompt to the local Qwen model through Ollama
    and returns the assistant's final customer-facing answer.
    """

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Agro-Mind, a concise agricultural support chatbot. "
                    "You do not write like a formal email. "
                    "Do not say 'Dear customer', 'Hello C001', 'Best regards', or 'Agro-Mind Team'. "
                    "Use a natural chatbot tone. "
                    "Only use the provided tool results. "
                    "Do not invent products, order details, prices, pesticide instructions, or diagnoses. "
                    "If no exact product match exists, say that clearly. "
                    "If a product is only a general support product, do not present it as a guaranteed solution. "
                    "If escalation is required, clearly say a human expert should review or confirm the case. "
                    "For pesticide, chemical, harvest, dosage, or food safety questions, avoid giving exact safety guarantees. "
                    "Recommend checking the product label and consulting an expert when risk exists. "
                    "Keep the answer short, clear, safe, and practical."
                    "Never provide exact pesticide waiting periods, dosage amounts, or food safety guarantees unless they are explicitly provided in the tool results. "
                ),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
    )

    return response["message"]["content"]