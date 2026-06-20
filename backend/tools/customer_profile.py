import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


CUSTOMERS_FILE = Path(__file__).resolve().parents[1] / "data" / "customers.jsonl"

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
        "customer_id": customer_id,
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


def load_customers() -> List[Dict[str, Any]]:
    customers = []

    if not CUSTOMERS_FILE.exists():
        return customers

    with open(CUSTOMERS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                customers.append(json.loads(line))

    return customers


def save_customers(customers: List[Dict[str, Any]]) -> None:
    CUSTOMERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(CUSTOMERS_FILE, "w", encoding="utf-8") as file:
        for customer in customers:
            file.write(json.dumps(customer, ensure_ascii=False) + "\n")


def get_customer_profile(customer_id: str) -> Optional[Dict[str, Any]]:
    customers = load_customers()

    for customer in customers:
        if str(customer.get("customer_id")) == str(customer_id):
            return customer

    return None


def create_profile(customer_id: str) -> Dict[str, Any]:
    customers = load_customers()
    profile = _default_profile(customer_id)

    customers.append(profile)
    save_customers(customers)

    return profile


def save_customer_profile(customer_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    customers = load_customers()
    updated = False

    for index, customer in enumerate(customers):
        if str(customer.get("customer_id")) == str(customer_id):
            customers[index] = profile
            updated = True
            break

    if not updated:
        customers.append(profile)

    save_customers(customers)
    return profile


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
        profile = _default_profile(customer_id)

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
    profile["common_issues"] = _compact_profile_list(profile.get("common_issues", []), MAX_ISSUES)
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

    save_customer_profile(customer_id, profile)

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