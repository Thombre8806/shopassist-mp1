"""ShopAssist's tools - YOU own this file.

Three tools, all READ-ONLY: they look things up and check rules. None of them cancels, refunds or changes anything -
actions that change data need a human approval step (Module 6), so customers do those on the website.

Remember Session 21, Section 7: type hints catch "abc", but they don't catch a WRONG VALUE. A tool that gets a
nonsense argument must RAISE ValueError with a message that says what's wrong. agent.run_tool() turns that into an
"INVALID: ..." message for the model, so the model asks the customer instead of guessing (S20's Fix B).
"""
import json
import re
from datetime import date
from pathlib import Path

from langchain_core.tools import tool

DATA = json.loads((Path(__file__).resolve().parents[1] / "data" / "orders.json").read_text(encoding="utf-8"))
ORDERS = {o["order_id"]: o for o in DATA["orders"]}
TODAY = date.fromisoformat(DATA["store_today"])          # fixed, so every run gives the same answers

RETURN_WINDOW_DAYS = 10                                  # normal returns: within 10 days of delivery
DAMAGED_WINDOW_DAYS = 30                                 # damaged / defective / wrong item: within 30 days
NON_RETURNABLE = {"innerwear", "groceries", "gift_cards"}
REASONS = {"wrong_size", "changed_mind", "damaged", "defective", "wrong_item", "not_as_described"}
ORDER_ID = re.compile(r"^ORD-\d{5}$")
METRO_PREFIXES = {"11", "40", "50", "56", "60", "70"}    # Delhi, Mumbai, Hyderabad, Bengaluru, Chennai, Kolkata


def _find(order_id: str) -> dict:
     """
    Validate order ID type, format, and existence.
    Args:
        order_id: Customer's order ID.
    Returns: 
        True if the order exists and is valid.
    """
     if not isinstance(order_id, str):
       raise ValueError( 
            f"order_id must be a string, got {type(order_id).__name__}"
       )
        
     if not re.fullmatch(r"ORD-\d{5}", order_id):
        raise ValueError(
             f"Invalid order ID format: {order_id}. Expected ORD-12345."
        )

     if order_id not in ORDERS:
        raise ValueError(
            f"no order {order_id} - ask the customer to check the order number"
        )
     
     return ORDERS[order_id]


@tool(parse_docstring=True)
def get_order_status(order_id: str) -> dict:
    """Status of ONE order: placed, shipped, out for delivery, delivered or cancelled, with its dates. Use when the
    customer asks where their order is or when it will arrive. Do NOT use it for general policy questions.

    Args:
        order_id: the order number exactly as the customer gave it, e.g. ORD-10233
    """
    o = _find(order_id)
    keys = ("order_id", "item", "status", "ordered_on", "delivered_on", "expected_delivery", "cancelled_on")
    return {k: o[k] for k in keys if k in o} | {"store_today": TODAY.isoformat()}


@tool(parse_docstring=True)
def get_delivery_estimate(pincode: str, speed: str = "standard") -> dict:
    """How many working days delivery takes to an Indian pincode, and what it costs. Use when the customer asks how
    long delivery will take to their area, or the price of express delivery.

    Args:
        pincode: the 6-digit Indian postal code, e.g. 500081
        speed: "standard" or "express"
    """
    if not isinstance(pincode, str):
        raise ValueError(
            f"pincode must be a string, got {type(pincode).__name__}"
        )

    if not re.fullmatch(r"\d{6}", pincode):
        raise ValueError(
            f"invalid pincode format: {pincode}, must be exactly 6 digits"
        )

    metro = pincode[:2] in METRO_PREFIXES

    if speed not in {"standard", "express"}:
        raise ValueError(
            f"Invalid speed '{speed}'. "
            "Allowed values are: standard, express"
        )
    if speed == "express":
        return {"pincode": pincode, "speed": "express", "days": "next day" if metro else "2-3 working days",
                "charge_rupees": 99}
    return {"pincode": pincode, "speed": "standard", "days": "2-3 working days" if metro else "4-6 working days",
            "charge_rupees": 0, "note": "free standard delivery on orders above Rs 499; Rs 49 below that"}



@tool(parse_docstring=True)
def check_return_eligibility(order_id: str, reason: str) -> dict:
    """
    Check whether a customer's order is eligible for a return or refund.

    Use this tool whenever a customer asks whether an existing order
    can be returned or refunded.

    The tool checks:
    1. Whether the order exists.
    2. Whether the order has been delivered.
    3. Whether the product category is returnable.
    4. Whether the request falls within the applicable return window.
    5. The potential refund amount.

    Do not use this tool for order tracking, cancellations before delivery,
    or general questions about return policies.

    Args:
        order_id: The customer's order ID, such as ORD-10231.
        reason: The reason for requesting a return. Allowed values are:
            damaged, defective, wrong_item, changed_mind,
            not_as_described.

    Returns:
        A dictionary containing eligibility, the reason for the decision,
        applicable return window, and refund information when eligible.

    Raises:
        ValueError: If the supplied return reason is invalid.
    """

    if reason not in REASONS:
       raise ValueError(
        f"Invalid reason '{reason}'. "
        f"Allowed values are: {', '.join(sorted(REASONS))}"
    )

    o = _find(order_id)

    if o["status"] != "delivered":
        return {
            "eligible": False,
            "why": f"Order has not been delivered yet. Current status: {o['status']}"
        }

    if o["category"] in NON_RETURNABLE:

        return {
        "eligible": False,
        "order_id": order_id,
        "return_reason": reason,
        "category": o["category"],
        "why": (
            f"{o['category']} products are non-returnable "
            "under our return policy."
        ),
        "refund_rupees": 0,
        "next_step": "Contact customer support if you received a defective item."
        }

    window = (
        DAMAGED_WINDOW_DAYS
        if reason in {"damaged", "defective", "wrong_item"}
        else RETURN_WINDOW_DAYS
    )

    days = (
        TODAY - date.fromisoformat(o["delivered_on"])
    ).days

    if days > window:
        return {
            "eligible": False,
            "why": f"Delivered {days} days ago; window is {window} days"
        }

    return {
        "eligible": True,
        "days_since_delivery": days,
        "window_days": window,
        "refund_rupees": o["price"],
        "how": "Start the return on the website: My Orders > Return"
    }




TOOLS = {"get_order_status": get_order_status, "get_delivery_estimate": get_delivery_estimate,
         "check_return_eligibility": check_return_eligibility}
