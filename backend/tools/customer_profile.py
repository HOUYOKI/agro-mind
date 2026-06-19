import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


CUSTOMERS_FILE = Path(__file__).resolve().parents[1] / "data" / "customers.jsonl"


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


def _append_unique(items: List[Any], value: Any) -> None:
    if value is None:
        return

    if isinstance(value, str) and not value.strip():
        return

    if value not in items:
        items.append(value)


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

    order_id = update_data.get("order_id")
    if order_id:
        order_exists = any(
            str(order.get("order_id")) == str(order_id)
            for order in profile["orders"]
        )

        if not order_exists:
            profile["orders"].append({"order_id": str(order_id)})

    _append_unique(profile["crops"], update_data.get("crop"))
    _append_unique(profile["common_issues"], update_data.get("possible_issue"))
    _append_unique(profile["recommended_products"], update_data.get("recommended_product"))

    if update_data.get("last_intent") == "complaint":
        profile["complaints_count"] = int(profile.get("complaints_count", 0)) + 1

    if update_data.get("human_escalation_requested") or update_data.get("escalation_required"):
        profile["human_escalation_requested"] = True

    escalation_case_id = update_data.get("escalation_case_id")

    if escalation_case_id:
        if escalation_case_id not in profile["escalation_case_ids"]:
            profile["escalation_case_ids"].append(escalation_case_id)
            profile["escalations_count"] = int(profile.get("escalations_count", 0)) + 1

    profile["last_interaction"] = datetime.now().date().isoformat()

    crops = ", ".join(profile.get("crops", [])) or "unknown crops"
    issues = ", ".join(profile.get("common_issues", [])) or "general support needs"
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

    Important:
    We intentionally do NOT include preferred_language here.
    The chatbot should answer in the language of the current message,
    not the saved customer language preference.
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
Customer segment: {profile.get("customer_segment")}
Upsell opportunity: {profile.get("upsell_opportunity")}
Summary: {profile.get("profile_summary", "")}
""".strip()