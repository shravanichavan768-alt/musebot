import uuid

def create_mock_payment_order(amount: float) -> dict:
    
    return {
        "order_id": f"order_mock_{uuid.uuid4().hex[:12]}",
        "amount": amount,
        "currency": "INR",
        "status": "created"
    }

def confirm_mock_payment(order_id: str) -> dict:
    
    return {
        "payment_id": f"pay_mock_{uuid.uuid4().hex[:12]}",
        "order_id": order_id,
        "status": "paid"
    }