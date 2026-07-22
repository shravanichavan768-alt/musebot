import os
import razorpay

client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))

def create_payment_order(amount: float) -> dict:
    order = client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "payment_capture": 1
    })
    return {
        "order_id": order["id"],
        "amount": amount,
        "currency": "INR",
        "status": order["status"],
        "razorpay_key_id": os.getenv("RAZORPAY_KEY_ID")
    }

def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False