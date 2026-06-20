import ollama
import re
import time

MODEL_NAME = "qwen2.5:7b-instruct"


def detect_language(text: str) -> str:
    if re.search(r"[\u0600-\u06FF]", text):
        return "Arabic"

    if re.search(r"[\u4E00-\u9FFF]", text):
        return "Chinese"

    return "English"


def ask_agro_mind(user_message: str) -> str:

    language = detect_language(user_message)

    start = time.perf_counter()

    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Agro-Mind, an agricultural support assistant. "
                    "Only use the information provided in tool outputs. "
                    "Never invent products, diagnoses, dosages, prices, or shipping details. "
                    "Keep answers concise, practical, and safe."
                ),
            },
            {
                "role": "system",
                "content": (
                    f"IMPORTANT: Respond ONLY in {language}. "
                    "Never answer in any other language."
                ),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
        options={
            "temperature": 0.1,
             "num_predict": 120
        },
    )

    elapsed = time.perf_counter() - start

    print(f"\n🔥 OLLAMA RESPONSE TIME: {elapsed:.2f} sec")

    return response["message"]["content"].strip()