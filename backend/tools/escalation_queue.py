from pathlib import Path
from datetime import datetime
from uuid import uuid4
import json
from typing import Optional, Dict, Any, List


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ESCALATION_FILE = DATA_DIR / "escalations.jsonl"


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _read_all() -> List[Dict[str, Any]]:
    if not ESCALATION_FILE.exists():
        return []

    rows = []

    with ESCALATION_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return rows


def _write_all(rows: List[Dict[str, Any]]) -> None:
    with ESCALATION_FILE.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def create_escalation_case(
    customer_id: str,
    case_type: str,
    reason: str,
    ai_response: str,
    source: str = "chat",
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    case = {
        "case_id": f"ESC-{uuid4().hex[:8].upper()}",
        "customer_id": customer_id or "unknown",
        "type": case_type or "support",
        "reason": reason or "Human review required.",
        "ai_response": ai_response or "",
        "status": "pending",
        "source": source,
        "created_at": _now(),
        "reviewed_at": None,
        "reviewer_note": None,
        "payload": payload or {},
    }

    with ESCALATION_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(case, ensure_ascii=False) + "\n")

    return case


def list_escalations(status: Optional[str] = "pending") -> List[Dict[str, Any]]:
    rows = _read_all()

    if status and status != "all":
        rows = [row for row in rows if row.get("status") == status]

    return sorted(rows, key=lambda item: item.get("created_at", ""), reverse=True)


def mark_escalation_reviewed(
    case_id: str,
    reviewer_note: Optional[str] = None,
) -> Dict[str, Any]:
    rows = _read_all()

    for row in rows:
        if row.get("case_id") == case_id:
            row["status"] = "reviewed"
            row["reviewed_at"] = _now()
            row["reviewer_note"] = reviewer_note
            _write_all(rows)
            return row

    raise ValueError(f"Escalation case not found: {case_id}")