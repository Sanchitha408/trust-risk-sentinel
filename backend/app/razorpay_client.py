"""
Thin wrapper around the Razorpay Python SDK, test-mode only.
"""

import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

KEY_ID = os.getenv("RAZORPAY_KEY_ID")
KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not KEY_ID or not KEY_SECRET:
    raise RuntimeError(
        "Missing RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET. "
        "Add them to backend/.env (use your TEST mode keys)."
    )

client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))


def create_test_order(amount_inr: float, receipt_id: str) -> dict:
    order = client.order.create(
        {
            "amount": int(amount_inr * 100),
            "currency": "INR",
            "receipt": receipt_id,
            "payment_capture": 1,
        }
    )
    return order
