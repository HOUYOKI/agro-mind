import re
from pathlib import Path

import pandas as pd


ORDERS_FILE = Path(__file__).resolve().parent.parent / "data" / "orders.csv"


def extract_order_id(message: str) -> str | None:
    """
    Extracts a 4+ digit order ID from the customer message.
    Example: 'Where is order 1001?' -> '1001'
    """
    match = re.search(r"\b\d{4,}\b", message)
    if match:
        return match.group(0)

    return None


def lookup_order(message: str, customer_id: str) -> dict:
    """
    Looks up order information from mock orders.csv.

    Priority:
    1. If message contains an order ID, search by order_id.
    2. If no order ID, return the latest order for the customer_id.
    """

    try:
        orders = pd.read_csv(ORDERS_FILE, dtype=str)
    except FileNotFoundError:
        return {
            "order_found": False,
            "order_id": None,
            "status": None,
            "eta": None,
            "tracking_number": None,
            "reason": "orders.csv file was not found."
        }

    order_id = extract_order_id(message)

    if order_id:
        matched_orders = orders[orders["order_id"] == order_id]

        if matched_orders.empty:
            return {
                "order_found": False,
                "order_id": order_id,
                "status": None,
                "eta": None,
                "tracking_number": None,
                "reason": f"No order found with order ID {order_id}."
            }

        order = matched_orders.iloc[0]

        return {
            "order_found": True,
            "order_id": order["order_id"],
            "status": order["status"],
            "eta": order["eta"],
            "tracking_number": order["tracking_number"],
            "reason": "Order found by order ID."
        }

    customer_orders = orders[orders["customer_id"] == customer_id]

    if customer_orders.empty:
        return {
            "order_found": False,
            "order_id": None,
            "status": None,
            "eta": None,
            "tracking_number": None,
            "reason": f"No orders found for customer {customer_id}."
        }

    latest_order = customer_orders.iloc[-1]

    return {
        "order_found": True,
        "order_id": latest_order["order_id"],
        "status": latest_order["status"],
        "eta": latest_order["eta"],
        "tracking_number": latest_order["tracking_number"],
        "reason": "No order ID provided. Returned latest order for this customer."
    }