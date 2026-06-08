import json
from pathlib import Path

import pandas as pd


JSONL_DIR = Path("client_data/jsonl")
OUTPUT_DIR = Path("client_data/jsonl_outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


CATEGORY_MAP = {
    "cat1_usage_product_real": "product_usage",
    "cat2_diagnosis_real": "crop_diagnosis",
    "cat3_aftersales_logistics_real": "aftersales_logistics",
    "cat4_safety_sensitive_real": "safety_sensitive",
}


def get_category(file_stem: str) -> str:
    for key, category in CATEGORY_MAP.items():
        if key in file_stem:
            return category
    return "unknown"


def extract_messages(record):
    """
    Supports common JSONL chat formats.
    Returns user messages, assistant messages, and full conversation text.
    """

    user_messages = []
    assistant_messages = []
    full_conversation = []

    # Format 1: {"messages": [{"role": "...", "content": "..."}]}
    if isinstance(record, dict) and "messages" in record:
        messages = record.get("messages", [])

        for message in messages:
            role = message.get("role", "unknown")
            content = message.get("content", "")

            if not content:
                continue

            if role == "user":
                user_messages.append(content)
            elif role == "assistant":
                assistant_messages.append(content)

            full_conversation.append(f"{role}: {content}")

    # Format 2: {"conversations": [...]}
    elif isinstance(record, dict) and "conversations" in record:
        messages = record.get("conversations", [])

        for message in messages:
            role = message.get("role") or message.get("from") or "unknown"
            content = message.get("content") or message.get("value") or ""

            if not content:
                continue

            normalized_role = "user" if role in ["human", "user"] else "assistant"

            if normalized_role == "user":
                user_messages.append(content)
            else:
                assistant_messages.append(content)

            full_conversation.append(f"{normalized_role}: {content}")

    # Format 3: simple question/answer
    elif isinstance(record, dict):
        possible_user = (
            record.get("user")
            or record.get("question")
            or record.get("input")
            or record.get("prompt")
            or record.get("instruction")
            or ""
        )

        possible_assistant = (
            record.get("assistant")
            or record.get("answer")
            or record.get("output")
            or record.get("response")
            or ""
        )

        if possible_user:
            user_messages.append(str(possible_user))
            full_conversation.append(f"user: {possible_user}")

        if possible_assistant:
            assistant_messages.append(str(possible_assistant))
            full_conversation.append(f"assistant: {possible_assistant}")

    return user_messages, assistant_messages, full_conversation


def process_file(file_path: Path):
    rows = []
    category = get_category(file_path.stem)

    with file_path.open("r", encoding="utf-8") as file:
        for session_index, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                rows.append({
                    "source_file": file_path.name,
                    "category": category,
                    "session_id": session_index,
                    "valid_json": False,
                    "error": str(error),
                    "user_messages": "",
                    "assistant_messages": "",
                    "full_conversation": line[:1000],
                })
                continue

            user_messages, assistant_messages, full_conversation = extract_messages(record)

            rows.append({
                "source_file": file_path.name,
                "category": category,
                "session_id": session_index,
                "valid_json": True,
                "error": "",
                "user_messages": " | ".join(user_messages),
                "assistant_messages": " | ".join(assistant_messages),
                "full_conversation": "\n".join(full_conversation),
            })

    return rows


def main():
    all_rows = []

    jsonl_files = sorted(JSONL_DIR.glob("*.jsonl"))

    if not jsonl_files:
        print(f"No JSONL files found in: {JSONL_DIR}")
        return

    for file_path in jsonl_files:
        print(f"Processing: {file_path.name}")
        rows = process_file(file_path)
        all_rows.extend(rows)

        df_file = pd.DataFrame(rows)
        output_file = OUTPUT_DIR / f"{file_path.stem}_examples.csv"
        df_file.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"Saved: {output_file}")

    df_all = pd.DataFrame(all_rows)
    output_all = OUTPUT_DIR / "all_jsonl_examples.csv"
    df_all.to_csv(output_all, index=False, encoding="utf-8-sig")

    print("\nDone.")
    print(f"Total sessions extracted: {len(df_all)}")
    print(f"Saved combined file: {output_all}")


if __name__ == "__main__":
    main()