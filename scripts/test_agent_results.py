from pathlib import Path
import sys

import pandas as pd


# Allow this script to import from backend/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from backend.tools.intent_classifier import classify_intent
from backend.tools.safety_checker import check_safety


# Change ONLY this path when switching test files
TEST_FILE = Path("client_data/evaluation/agromind_random_test_03.csv")

# Used only if TEST_FILE is Excel
SHEET_NAME = "Test Messages"


def normalize(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def load_test_file(file_path: Path) -> pd.DataFrame:
    """
    Loads test data from either CSV or Excel.

    Supported:
    - .csv
    - .xlsx
    - .xls
    """

    if not file_path.exists():
        raise FileNotFoundError(f"Test file not found: {file_path}")

    file_extension = file_path.suffix.lower()

    if file_extension == ".csv":
        return pd.read_csv(file_path)

    if file_extension in [".xlsx", ".xls"]:
        return pd.read_excel(file_path, sheet_name=SHEET_NAME)

    raise ValueError(
        f"Unsupported file type: {file_extension}. Use .csv, .xlsx, or .xls"
    )


def main():
    try:
        df = load_test_file(TEST_FILE)
    except Exception as error:
        print("Failed to load test file.")
        print(error)
        return

    required_columns = [
        "message_en",
        "message_original",
        "expected_intent",
        "expected_risk",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print("Missing required columns:")
        for col in missing_columns:
            print(f"- {col}")
        print("\nYour file must contain these columns:")
        print(", ".join(required_columns))
        return

    total = len(df)
    passed_intent = 0
    passed_risk = 0

    failed_rows = []

    print("=" * 90)
    print("Agro-Mind Rule Test Results")
    print("=" * 90)
    print(f"Test file: {TEST_FILE}")
    print(f"Total rows: {total}")

    for index, row in df.iterrows():
        message_en = normalize(row.get("message_en"))
        message_original = normalize(row.get("message_original"))

        # Prefer English because current prototype rules are mostly English.
        # If English is missing, use the original message.
        message = message_en or message_original

        expected_intent = normalize(row.get("expected_intent"))
        expected_risk = normalize(row.get("expected_risk"))

        predicted_intent = classify_intent(message)
        safety_result = check_safety(message, predicted_intent)
        predicted_risk = safety_result.get("risk_level", "")

        intent_ok = predicted_intent == expected_intent
        risk_ok = predicted_risk == expected_risk

        if intent_ok:
            passed_intent += 1

        if risk_ok:
            passed_risk += 1

        status = "PASS" if intent_ok and risk_ok else "FAIL"

        print(f"\n[{status}] Row {index + 1}")
        print(f"Message: {message}")
        print(f"Expected intent: {expected_intent}")
        print(f"Predicted intent: {predicted_intent}")
        print(f"Expected risk: {expected_risk}")
        print(f"Predicted risk: {predicted_risk}")

        if not intent_ok or not risk_ok:
            print("Needs rule update.")
            failed_rows.append(
                {
                    "row": index + 1,
                    "message": message,
                    "expected_intent": expected_intent,
                    "predicted_intent": predicted_intent,
                    "expected_risk": expected_risk,
                    "predicted_risk": predicted_risk,
                }
            )

    print("\n" + "=" * 90)
    print("Summary")
    print("=" * 90)
    print(f"Total test messages: {total}")
    print(f"Intent accuracy: {passed_intent}/{total}")
    print(f"Risk accuracy: {passed_risk}/{total}")

    if failed_rows:
        print("\n" + "=" * 90)
        print("Failed Rows Only")
        print("=" * 90)

        for failed in failed_rows:
            print(f"\nRow {failed['row']}")
            print(f"Message: {failed['message']}")
            print(
                f"Intent: expected {failed['expected_intent']} | "
                f"predicted {failed['predicted_intent']}"
            )
            print(
                f"Risk: expected {failed['expected_risk']} | "
                f"predicted {failed['predicted_risk']}"
            )


if __name__ == "__main__":
    main()