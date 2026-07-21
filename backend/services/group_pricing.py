PRICE_PER_ADULT = 200
PRICE_PER_KID = 100

def calculate_group_price(headcount: int, is_school: bool = False) -> dict:
    
    base_amount = headcount * PRICE_PER_ADULT

    if is_school:
        
        discount_percent = 30
    elif headcount >= 50:
        discount_percent = 25
    elif headcount >= 20:
        discount_percent = 15
    elif headcount >= 10:
        discount_percent = 8
    else:
        discount_percent = 0

    final_amount = round(base_amount * (1 - discount_percent / 100), 2)

    return {
        "headcount": headcount,
        "base_amount": base_amount,
        "discount_percent": discount_percent,
        "final_amount": final_amount,
        "per_head_price": round(final_amount / headcount, 2) if headcount else 0
    }