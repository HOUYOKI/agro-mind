"""
Confirm that safety_checker.py Tier 4 (Qwen fallback) fails CLOSED:
when requests.post raises an exception, check_safety() must return
risk_level="medium" and escalation_required=True — never "low"/False.

Run from the project root:
    python scripts/test_safety_tier4_failclosed.py
"""

import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tools.safety_checker import check_safety


MESSAGE = "How often should I water my citrus trees?"
INTENT = "general_question"


def run():
    print()
    print("=" * 60)
    print("  Tier 4 fail-closed test")
    print(f"  message: {MESSAGE!r}")
    print("=" * 60)
    print()

    with patch("backend.tools.safety_checker.requests.post",
               side_effect=ConnectionError("mocked Qwen unreachable")):
        result = check_safety(MESSAGE, INTENT)

    print(f"  risk_level         : {result['risk_level']!r}")
    print(f"  escalation_required: {result['escalation_required']}")
    print(f"  reason             : {result['reason']}")
    print()

    risk_ok = result["risk_level"] == "medium"
    esc_ok = result["escalation_required"] is True

    if risk_ok and esc_ok:
        print("  PASS — Tier 4 fails closed (medium / escalation_required=True)")
    else:
        failures = []
        if not risk_ok:
            failures.append(f"risk_level={result['risk_level']!r}, want 'medium'")
        if not esc_ok:
            failures.append(f"escalation_required={result['escalation_required']}, want True")
        print(f"  FAIL — {'; '.join(failures)}")

    print()
    print("=" * 60)
    print()


if __name__ == "__main__":
    run()
