from datetime import datetime

def calculate_refund_amount(total_amount: float, visit_date: str) -> dict:
    
    try:
        visit_dt = datetime.strptime(visit_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return {"eligible": False, "refund_amount": 0, "reason": "Invalid visit date"}

    hours_until_visit = (visit_dt - datetime.now()).total_seconds() / 3600

    if hours_until_visit < 0:
        return {"eligible": False, "refund_amount": 0, "reason": "Visit date has already passed"}
    elif hours_until_visit >= 48:
        return {"eligible": True, "refund_amount": total_amount, "refund_percent": 100, "reason": "Full refund — cancelled 48+ hours in advance"}
    elif hours_until_visit >= 24:
        return {"eligible": True, "refund_amount": round(total_amount * 0.5, 2), "refund_percent": 50, "reason": "Partial refund — cancelled 24-48 hours in advance"}
    else:
        return {"eligible": False, "refund_amount": 0, "reason": "No refund — less than 24 hours before visit"}