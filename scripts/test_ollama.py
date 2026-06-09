import ollama

response = ollama.chat(
    model="qwen2.5:7b-instruct",
    messages=[
        {
            "role": "system",
            "content": "You are Agro-Mind, a safe agriculture support assistant. Answer clearly and avoid unsafe pesticide advice."
        },
        {
            "role": "user",
            "content": "My tomato leaves are yellow and curling. What should I do?"
        }
    ]
)

print(response["message"]["content"])