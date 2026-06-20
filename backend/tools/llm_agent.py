import re
import time
import ollama


MODEL_NAME = "qwen2.5:7b-instruct"


SYSTEM_PROMPT = (
    "You are Agro-Mind, a concise agricultural support chatbot. "
    "Use a natural chatbot tone, not a formal email style. "
    "Do not say 'Dear customer', 'Hello C001', 'Best regards', or 'Agro-Mind Team'. "
    "Only use the provided tool results. "
    "Do not invent products, diagnoses, order details, prices, pesticide instructions, or safety claims. "
    "If no exact product match exists, say that clearly. "
    "If a product is only a general support product, do not present it as a guaranteed solution. "
    "If escalation is required, clearly say a human expert should review or confirm the case. "
    "For pesticide, chemical, harvest, dosage, or food safety questions, avoid exact guarantees. "
    "Never provide exact pesticide waiting periods, dosage amounts, dilution ratios, application intervals, "
    "or food safety guarantees unless they are explicitly provided in the tool results. "
    "Recommend checking the product label and consulting an expert when risk exists. "
    "Keep the answer short, clear, safe, and practical."
)


def detect_language(text: str) -> str:
    text = text or ""

    if re.search(r"[\u0600-\u06FF]", text):
        return "Arabic"

    if re.search(r"[\u4E00-\u9FFF]", text):
        return "Chinese"

    return "English"


def ask_agro_mind(user_message: str) -> str:
    """
    LLM-first response generation.

    Important:
    This function does NOT return a rule-based fallback.
    If Ollama/Qwen fails, it raises the error.
    agent_graph.py is responsible for catching that error and using fallback only then.
    """
    language = detect_language(user_message)
    start = time.perf_counter()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "system",
            "content": (
                f"Respond ONLY in {language}. "
                "Never answer in another language."
            ),
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

    try:
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages,
                options={
                    "temperature": 0.1,
                    "num_predict": 180,
                    "num_ctx": 4096,
                },
                keep_alive="10m",
            )

        except TypeError:
            # Older ollama package versions may not support keep_alive.
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages,
                options={
                    "temperature": 0.1,
                    "num_predict": 180,
                    "num_ctx": 4096,
                },
            )

        elapsed = time.perf_counter() - start
        print(f"\nOLLAMA RESPONSE TIME: {elapsed:.2f} sec")

        return response["message"]["content"].strip()

    except Exception as error:
        elapsed = time.perf_counter() - start
        print(f"\nOLLAMA FAILED AFTER {elapsed:.2f} sec:", error)
        raise