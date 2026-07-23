from database import exhibits_collection

async def get_bundle_suggestion(venue_id, current_exhibit_id, current_category: str):
    
    from bson import ObjectId
    candidates = await exhibits_collection.find({
        "venueId": ObjectId(venue_id) if isinstance(venue_id, str) else venue_id,
        "_id": {"$ne": ObjectId(current_exhibit_id) if isinstance(current_exhibit_id, str) else current_exhibit_id},
        "active": True
    }).to_list(20)

    if not candidates:
        return None

    # Prefer a different category for variety, else just take the first other exhibit
    different_category = [c for c in candidates if c.get("category") != current_category]
    pick = different_category[0] if different_category else candidates[0]

    return {
        "exhibit_id": str(pick["_id"]),
        "exhibit_name": pick["name"],
        "category": pick["category"],
        "base_price": pick["basePrice"]
    }