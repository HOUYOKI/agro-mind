import json
import re
from pathlib import Path
from typing import Optional, Dict, Any


ORDERS_FILE = Path(__file__).resolve().parents[1] / "data" / "orders.jsonl"


def load_orders():
    orders = []

    if not ORDERS_FILE.exists():
        return orders

    with open(ORDERS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                orders.append(json.loads(line))

    return orders


def extract_order_id(message: str) -> Optional[str]:
    """
    Extract a likely order ID from the customer message.

    Supports:
    - 1001
    - order 1001
    - ORD001
    - ORD-1001
    """
    message = message.strip()

    # Match normal numeric order IDs like 1001, 1002, etc.
    numeric_match = re.search(r"\b\d{4,}\b", message)
    if numeric_match:
        return numeric_match.group(0)

    # Match IDs like ORD001 or ORD-1001
    ord_match = re.search(r"\bORD[-]?\d+\b", message, re.IGNORECASE)
    if ord_match:
        return ord_match.group(0).upper().replace("ORD-", "ORD")

    return None


def lookup_order(message: str, customer_id: str) -> Dict[str, Any]:
    orders = load_orders()
    requested_order_id = extract_order_id(message)

    # 1. If user explicitly mentions an order ID, respect it first.
    if requested_order_id:
        for order in orders:
            order_id = str(order.get("order_id"))
            order_customer_id = str(order.get("customer_id"))

            if order_id == str(requested_order_id):
                # Found order, but wrong customer.
                if order_customer_id != str(customer_id):
                    return {
                        "order_found": False,
                        "order_id": None,
                        "status": None,
                        "eta": None,
                        "tracking_number": None,
                        "reason": (
                            f"Order {requested_order_id} was found, but it does not belong "
                            f"to customer {customer_id}. Please verify the order number or customer ID."
                        ),
                    }

                # Found order and customer matches.
                return {
                    "order_found": True,
                    "order_id": order.get("order_id"),
                    "status": order.get("status"),
                    "eta": order.get("eta"),
                    "tracking_number": order.get("tracking_number"),
                    "reason": (
                        f"The item '{order.get('product')}' is currently "
                        f"[{order.get('status')}] at {order.get('current_location')}."
                    ),
                }

        # User gave an order ID, but it does not exist.
        return {
            "order_found": False,
            "order_id": None,
            "status": None,
            "eta": None,
            "tracking_number": None,
            "reason": f"Order {requested_order_id} was not found in the logistics database.",
        }

    # 2. If no order ID was mentioned, fall back to customer_id.
    for order in orders:
        if str(order.get("customer_id")) == str(customer_id):
            return {
                "order_found": True,
                "order_id": order.get("order_id"),
                "status": order.get("status"),
                "eta": order.get("eta"),
                "tracking_number": order.get("tracking_number"),
                "reason": (
                    f"The item '{order.get('product')}' is currently "
                    f"[{order.get('status')}] at {order.get('current_location')}."
                ),
            }

    return {
        "order_found": False,
        "order_id": None,
        "status": None,
        "eta": None,
        "tracking_number": None,
        "reason": "Order or customer details not found in the logistics database.",
    }