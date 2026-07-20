def calculate_crowd_status(capacity: int, booked: int) -> dict:
    """
    Returns crowd status + discount based on how full a slot is.
    """
    if capacity <= 0:
        return {"status": "Quiet", "discountPercent": 0}

    fill_ratio = booked / capacity

    if fill_ratio >= 0.75:
        return {"status": "Busy", "discountPercent": 0}
    elif fill_ratio >= 0.4:
        return {"status": "Moderate", "discountPercent": 0}
    else:
        
        return {"status": "Quiet", "discountPercent": 15}