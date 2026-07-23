from fastapi import APIRouter, Query
from database import bookings_collection, slots_collection, exhibits_collection
from bson import ObjectId

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary(venue_id: str = Query(...)):
    venue_oid = ObjectId(venue_id)

    total_bookings = await bookings_collection.count_documents({"venueId": venue_oid})
    confirmed = await bookings_collection.count_documents({"venueId": venue_oid, "status": "confirmed"})
    checked_in = await bookings_collection.count_documents({"venueId": venue_oid, "status": "checked_in"})
    completed = await bookings_collection.count_documents({"venueId": venue_oid, "status": "completed"})
    cancelled = await bookings_collection.count_documents({"venueId": venue_oid, "status": "cancelled"})

    revenue_pipeline = [
        {"$match": {"venueId": venue_oid, "status": {"$in": ["confirmed", "checked_in", "completed"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$totalAmount"}}}
    ]
    revenue_result = await bookings_collection.aggregate(revenue_pipeline).to_list(1)
    total_revenue = revenue_result[0]["total"] if revenue_result else 0

    visitors_pipeline = [
        {"$match": {"venueId": venue_oid, "status": {"$in": ["confirmed", "checked_in", "completed"]}}},
        {"$group": {"_id": None, "adults": {"$sum": "$adults"}, "kids": {"$sum": "$kids"}}}
    ]
    visitors_result = await bookings_collection.aggregate(visitors_pipeline).to_list(1)
    total_visitors = (visitors_result[0]["adults"] + visitors_result[0]["kids"]) if visitors_result else 0

    no_show_rate = round((cancelled / total_bookings * 100), 1) if total_bookings > 0 else 0

    rating_pipeline = [
        {"$match": {"venueId": venue_oid, "feedbackRating": {"$ne": None}}},
        {"$group": {"_id": None, "avg": {"$avg": "$feedbackRating"}, "count": {"$sum": 1}}}
    ]
    rating_result = await bookings_collection.aggregate(rating_pipeline).to_list(1)
    avg_rating = round(rating_result[0]["avg"], 1) if rating_result else None
    rating_count = rating_result[0]["count"] if rating_result else 0

    return {
        "total_bookings": total_bookings,
        "confirmed": confirmed,
        "checked_in": checked_in,
        "completed": completed,
        "cancelled": cancelled,
        "total_revenue": total_revenue,
        "total_visitors": total_visitors,
        "no_show_rate_percent": no_show_rate,
        "avg_rating": avg_rating,
        "rating_count": rating_count
    }


@router.get("/popular-exhibits")
async def popular_exhibits(venue_id: str = Query(...)):
    venue_oid = ObjectId(venue_id)

    exhibits = await exhibits_collection.find({"venueId": venue_oid}).to_list(100)
    result = []
    for ex in exhibits:
        slots = await slots_collection.find({"exhibit": ex["_id"]}).to_list(500)
        slot_ids = [s["_id"] for s in slots]
        booking_count = await bookings_collection.count_documents({
            "slot": {"$in": slot_ids},
            "status": {"$in": ["confirmed", "checked_in", "completed"]}
        })
        result.append({"exhibit_name": ex["name"], "bookings": booking_count})

    result.sort(key=lambda x: x["bookings"], reverse=True)
    return result


@router.get("/peak-hours")
async def peak_hours(venue_id: str = Query(...)):
    venue_oid = ObjectId(venue_id)

    exhibits = await exhibits_collection.find({"venueId": venue_oid}).to_list(100)
    exhibit_ids = [e["_id"] for e in exhibits]

    slots = await slots_collection.find({"exhibit": {"$in": exhibit_ids}}).to_list(1000)

    hour_bookings = {}
    for s in slots:
        hour = s["startTime"]
        hour_bookings[hour] = hour_bookings.get(hour, 0) + max(0, s.get("booked", 0))

    result = [{"time": k, "bookings": v} for k, v in sorted(hour_bookings.items())]
    return result


@router.get("/footfall-trend")
async def footfall_trend(venue_id: str = Query(...)):
    venue_oid = ObjectId(venue_id)

    exhibits = await exhibits_collection.find({"venueId": venue_oid}).to_list(100)
    exhibit_ids = [e["_id"] for e in exhibits]

    slots = await slots_collection.find({"exhibit": {"$in": exhibit_ids}}).to_list(1000)

    date_bookings = {}
    for s in slots:
        date = s["date"]
        date_bookings[date] = date_bookings.get(date, 0) + max(0, s.get("booked", 0))

    result = [{"date": k, "visitors": v} for k, v in sorted(date_bookings.items())]
    return result