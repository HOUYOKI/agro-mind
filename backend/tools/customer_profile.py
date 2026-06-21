import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CUSTOMERS_FILE = DATA_DIR / "customers.jsonl"
CUSTOMERS_DB = DATA_DIR / "customer_profiles.db"

MAX_CROPS = 5
MAX_ISSUES = 5
MAX_PRODUCTS = 5

BAD_VALUES = {
    None,
    "",
    "Unknown",
    "unknown",
    "Error",
    "error",
    "CRITICAL: RAG Engine Error",
    "Consult an agricultural expert",
    "No product recommendation available",
    "Unknown Product",
}

BAD_PRODUCT_VALUES = {
    None,
    "",
    "Consult an agricultural expert",
    "CRITICAL: RAG Engine Error",
    "No product recommendation available",
    "Unknown Product",
    "Unknown",
    "Error",
}


def _default_profile(customer_id: str) -> Dict[str, Any]:
    return {
        "customer_id": str(customer_id),
        "orders": [],
        "crops": [],
        "common_issues": [],
        "recommended_products": [],
        "complaints_count": 0,
        "escalations_count": 0,
        "human_escalation_requested": False,
        "escalation_case_ids": [],
        "preferred_language": None,
        "last_interaction": None,
        "profile_summary": "",
        "customer_segment": "Regular",
        "upsell_opportunity": False,
    }


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(CUSTOMERS_DB)
    connection.row_factory = sqlite3.Row
    return connection


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Any, default: Any) -> Any:
    if value is None or value == "":
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def _bool_to_int(value: Any) -> int:
    return 1 if bool(value) else 0


def _int_to_bool(value: Any) -> bool:
    return bool(int(value or 0))


def init_customer_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_profiles (
                customer_id TEXT PRIMARY KEY,
                orders TEXT NOT NULL DEFAULT '[]',
                crops TEXT NOT NULL DEFAULT '[]',
                common_issues TEXT NOT NULL DEFAULT '[]',
                recommended_products TEXT NOT NULL DEFAULT '[]',
                complaints_count INTEGER NOT NULL DEFAULT 0,
                escalations_count INTEGER NOT NULL DEFAULT 0,
                human_escalation_requested INTEGER NOT NULL DEFAULT 0,
                escalation_case_ids TEXT NOT NULL DEFAULT '[]',
                preferred_language TEXT,
                last_interaction TEXT,
                profile_summary TEXT NOT NULL DEFAULT '',
                customer_segment TEXT NOT NULL DEFAULT 'Regular',
                upsell_opportunity INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def _row_to_profile(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "customer_id": row["customer_id"],
        "orders": _json_loads(row["orders"], []),
        "crops": _json_loads(row["crops"], []),
        "common_issues": _json_loads(row["common_issues"], []),
        "recommended_products": _json_loads(row["recommended_products"], []),
        "complaints_count": int(row["complaints_count"] or 0),
        "escalations_count": int(row["escalations_count"] or 0),
        "human_escalation_requested": _int_to_bool(
            row["human_escalation_requested"]
        ),
        "escalation_case_ids": _json_loads(row["escalation_case_ids"], []),
        "preferred_language": row["preferred_language"],
        "last_interaction": row["last_interaction"],
        "profile_summary": row["profile_summary"] or "",
        "customer_segment": row["customer_segment"] or "Regular",
        "upsell_opportunity": _int_to_bool(row["upsell_opportunity"]),
    }


def _insert_or_replace_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    init_customer_db()

    now = datetime.now().isoformat(timespec="seconds")
    customer_id = str(profile.get("customer_id"))

    with _connect() as connection:
        existing = connection.execute(
            "SELECT created_at FROM customer_profiles WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()

        created_at = existing["created_at"] if existing else now

        connection.execute(
            """
            INSERT OR REPLACE INTO customer_profiles (
                customer_id,
                orders,
                crops,
                common_issues,
                recommended_products,
                complaints_count,
                escalations_count,
                human_escalation_requested,
                escalation_case_ids,
                preferred_language,
                last_interaction,
                profile_summary,
                customer_segment,
                upsell_opportunity,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                _json_dumps(profile.get("orders", [])),
                _json_dumps(profile.get("crops", [])),
                _json_dumps(profile.get("common_issues", [])),
                _json_dumps(profile.get("recommended_products", [])),
                int(profile.get("complaints_count", 0)),
                int(profile.get("escalations_count", 0)),
                _bool_to_int(profile.get("human_escalation_requested", False)),
                _json_dumps(profile.get("escalation_case_ids", [])),
                profile.get("preferred_language"),
                profile.get("last_interaction"),
                profile.get("profile_summary", ""),
                profile.get("customer_segment", "Regular"),
                _bool_to_int(profile.get("upsell_opportunity", False)),
                created_at,
                now,
            ),
        )
        connection.commit()

    return profile


def migrate_customers_jsonl_to_sqlite() -> None:
    """
    One-time migration from backend/data/customers.jsonl into SQLite.
    Safe to run multiple times because customer_id is the primary key.
    """
    init_customer_db()

    if not CUSTOMERS_FILE.exists():
        return

    with open(CUSTOMERS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            try:
                profile = json.loads(line)
            except Exception:
                continue

            if not profile.get("customer_id"):
                continue

            base = _default_profile(str(profile.get("customer_id")))
            base.update(profile)
            _insert_or_replace_profile(base)


def _ensure_ready() -> None:
    init_customer_db()

    # If DB is empty and old JSONL exists, migrate automatically.
    with _connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) AS total FROM customer_profiles"
        ).fetchone()["total"]

    if count == 0 and CUSTOMERS_FILE.exists():
        migrate_customers_jsonl_to_sqlite()


def load_customers() -> List[Dict[str, Any]]:
    _ensure_ready()

    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM customer_profiles ORDER BY customer_id"
        ).fetchall()

    return [_row_to_profile(row) for row in rows]


def save_customers(customers: List[Dict[str, Any]]) -> None:
    """
    Keeps old function name for compatibility.
    Replaces all SQLite profiles with the provided list.
    """
    init_customer_db()

    with _connect() as connection:
        connection.execute("DELETE FROM customer_profiles")
        connection.commit()

    for customer in customers:
        if customer.get("customer_id"):
            base = _default_profile(str(customer.get("customer_id")))
            base.update(customer)
            _insert_or_replace_profile(base)


def get_customer_profile(customer_id: str) -> Optional[Dict[str, Any]]:
    _ensure_ready()

    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM customer_profiles WHERE customer_id = ?",
            (str(customer_id),),
        ).fetchone()

    if row is None:
        return None

    return _row_to_profile(row)


def create_profile(customer_id: str) -> Dict[str, Any]:
    profile = _default_profile(str(customer_id))
    _insert_or_replace_profile(profile)
    return profile


def save_customer_profile(customer_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    base = _default_profile(str(customer_id))
    base.update(profile)
    base["customer_id"] = str(customer_id)

    _insert_or_replace_profile(base)
    return base


def _is_garbled_text(value: str) -> bool:
    """
    Blocks mojibake/encoding-corrupted text like:
    è¾£æ¤’, æž¯é»„, etc.

    This does not block real Chinese characters.
    """
    if not isinstance(value, str):
        return False

    garbled_markers = ["Ã", "Â", "æ", "è", "é", "ç", "å", "ä", "ð", "�"]
    return any(marker in value for marker in garbled_markers)


def _is_too_broad_string(value: str) -> bool:
    """
    Blocks huge product metadata strings like:
    'Apple Trees, Fruit Trees, Vegetables, Field Crops, Rice...'

    These are product coverage metadata, not stable customer profile facts.
    """
    if not isinstance(value, str):
        return False

    comma_count = value.count(",")
    return comma_count >= 4 or len(value) > 120


def _clean_value(value: Any) -> Optional[str]:
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    if value in BAD_VALUES:
        return None

    if _is_garbled_text(value):
        return None

    if _is_too_broad_string(value):
        return None

    return value


def _append_unique(items: List[Any], value: Any, max_items: int) -> None:
    value = _clean_value(value)

    if not value:
        return

    if value not in items and len(items) < max_items:
        items.append(value)


def _append_list_safely(items: List[Any], value: Any, max_items: int) -> None:
    """
    Save small direct lists only.

    If RAG returns a huge list of crops/diseases, skip it because it is usually
    product metadata, not actual customer memory.
    """
    if value is None:
        return

    if isinstance(value, list):
        if len(value) > 3:
            return

        for item in value:
            _append_unique(items, item, max_items)

        return

    _append_unique(items, value, max_items)


def _append_product_if_valid(items: List[Any], value: Any) -> None:
    if value is None:
        return

    if isinstance(value, list):
        if len(value) > 3:
            return

        for item in value:
            _append_product_if_valid(items, item)

        return

    if isinstance(value, str):
        value = value.strip()

    if value in BAD_PRODUCT_VALUES:
        return

    cleaned = _clean_value(value)

    if not cleaned:
        return

    if cleaned not in items and len(items) < MAX_PRODUCTS:
        items.append(cleaned)


def _compact_profile_list(values: List[Any], max_items: int) -> List[Any]:
    clean_values = []

    for value in values:
        cleaned = _clean_value(value)

        if cleaned and cleaned not in clean_values:
            clean_values.append(cleaned)

        if len(clean_values) >= max_items:
            break

    return clean_values


def update_customer_profile(customer_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    profile = get_customer_profile(customer_id)

    if profile is None:
        profile = _default_profile(str(customer_id))

    profile.setdefault("orders", [])
    profile.setdefault("crops", [])
    profile.setdefault("common_issues", [])
    profile.setdefault("recommended_products", [])
    profile.setdefault("complaints_count", 0)
    profile.setdefault("escalations_count", 0)
    profile.setdefault("human_escalation_requested", False)
    profile.setdefault("escalation_case_ids", [])
    profile.setdefault("preferred_language", None)
    profile.setdefault("last_interaction", None)
    profile.setdefault("profile_summary", "")
    profile.setdefault("customer_segment", "Regular")
    profile.setdefault("upsell_opportunity", False)

    last_intent = update_data.get("last_intent")

    # Clean old polluted values every time the profile updates.
    profile["crops"] = _compact_profile_list(profile.get("crops", []), MAX_CROPS)
    profile["common_issues"] = _compact_profile_list(
        profile.get("common_issues", []),
        MAX_ISSUES,
    )
    profile["recommended_products"] = _compact_profile_list(
        profile.get("recommended_products", []),
        MAX_PRODUCTS,
    )

    # Save orders when available.
    order_id = update_data.get("order_id")

    if order_id:
        order_exists = any(
            str(order.get("order_id")) == str(order_id)
            for order in profile["orders"]
        )

        if not order_exists:
            profile["orders"].append({"order_id": str(order_id)})

    # Only save crop/issue/product memory for crop/product cases.
    # Do not let safety, complaint, or order cases pollute agronomy memory.
    if last_intent in {"crop_diagnosis", "product_question"}:
        crop_value = update_data.get("crop")
        issue_value = update_data.get("possible_issue")
        product_value = update_data.get("recommended_product")

        _append_list_safely(profile["crops"], crop_value, MAX_CROPS)
        _append_list_safely(profile["common_issues"], issue_value, MAX_ISSUES)
        _append_product_if_valid(profile["recommended_products"], product_value)

    if last_intent == "complaint":
        profile["complaints_count"] = int(profile.get("complaints_count", 0)) + 1

    if (
        update_data.get("human_escalation_requested")
        or update_data.get("escalation_required")
    ):
        profile["human_escalation_requested"] = True

    escalation_case_id = update_data.get("escalation_case_id")

    if escalation_case_id:
        if escalation_case_id not in profile["escalation_case_ids"]:
            profile["escalation_case_ids"].append(escalation_case_id)
            profile["escalations_count"] = int(profile.get("escalations_count", 0)) + 1

    profile["last_interaction"] = datetime.now().date().isoformat()

    crops = ", ".join(map(str, profile.get("crops", [])[:3])) or "unknown crops"
    issues = ", ".join(map(str, profile.get("common_issues", [])[:3])) or "general support needs"

    profile["profile_summary"] = f"Customer growing {crops} with {issues}."

    if profile["escalations_count"] > 0 or profile["complaints_count"] > 0:
        profile["customer_segment"] = "High Risk"
        profile["upsell_opportunity"] = False

    elif len(profile["orders"]) >= 2:
        profile["customer_segment"] = "High Value"
        profile["upsell_opportunity"] = True

    else:
        profile["customer_segment"] = "Regular"
        profile["upsell_opportunity"] = False

    save_customer_profile(str(customer_id), profile)

    return profile


def summarize_customer_profile(customer_id: str) -> str:
    """
    Summary for the LLM.

    preferred_language is kept as metadata, but the chatbot should answer
    in the language of the current message, not based on this stored value.
    """
    profile = get_customer_profile(customer_id)

    if not profile:
        return "No customer profile found."

    return f"""
Customer Profile:
Customer ID: {profile.get("customer_id")}
Crops: {profile.get("crops", [])}
Common issues: {profile.get("common_issues", [])}
Recommended products: {profile.get("recommended_products", [])}
Orders: {profile.get("orders", [])}
Complaints count: {profile.get("complaints_count", 0)}
Escalations count: {profile.get("escalations_count", 0)}
Human escalation requested: {profile.get("human_escalation_requested", False)}
Escalation case IDs: {profile.get("escalation_case_ids", [])}
Preferred language metadata: {profile.get("preferred_language")}
Customer segment: {profile.get("customer_segment")}
Upsell opportunity: {profile.get("upsell_opportunity")}
Summary: {profile.get("profile_summary", "")}
""".strip()