from fastapi import APIRouter, HTTPException
from bson import ObjectId
from database import bookings_collection, slots_collection, users_collection, exhibits_collection
from models.booking import Booking
from services.crowd_meter import calculate_crowd_status
from services.souvenir import generate_visit_badge

router = APIRouter(prefix="/api/bookings", tags=["bookings"])

@router.post("/")
async def create_booking(booking: Booking):
    slot = await slots_collection.find_one({"_id": ObjectId(booking.slot)})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    requested = booking.adults + booking.kids
    remaining = slot["capacity"] - slot["booked"]
    if requested > remaining:
        raise HTTPException(status_code=400, detail=f"Only {remaining} seats left in this slot")

    # Apply crowd-based discount to totalAmount
    crowd = calculate_crowd_status(slot["capacity"], slot["booked"])
    discount_multiplier = 1 - (crowd["discountPercent"] / 100)
    booking.totalAmount = round(booking.totalAmount * discount_multiplier, 2)

    doc = booking.model_dump(by_alias=True, exclude={"id"})
    doc["user"] = ObjectId(doc["user"])
    doc["slot"] = ObjectId(doc["slot"])
    result = await bookings_collection.insert_one(doc)

    await slots_collection.update_one(
        {"_id": ObjectId(booking.slot)},
        {"$inc": {"booked": requested}}
    )

    return {"id": str(result.inserted_id), "status": "pending", "totalAmount": booking.totalAmount}

@router.get("/{booking_id}")
async def get_booking(booking_id: str):
    booking = await bookings_collection.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking["_id"] = str(booking["_id"])
    booking["user"] = str(booking["user"])
    booking["slot"] = str(booking["slot"])
    return booking

@router.patch("/{booking_id}/status")
async def update_status(booking_id: str, status: str):
    result = await bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"id": booking_id, "status": status}

@router.post("/{booking_id}/checkin")
async def checkin(booking_id: str):
    result = await bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "checked_in"}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"id": booking_id, "status": "checked_in"}

@router.post("/{booking_id}/checkout")
async def checkout(booking_id: str):
    booking = await bookings_collection.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    user = await users_collection.find_one({"_id": booking["user"]})
    slot = await slots_collection.find_one({"_id": booking["slot"]})
    exhibit = await exhibits_collection.find_one({"_id": slot["exhibit"]}) if slot else None

    visitor_name = user["name"] if user else "Visitor"
    exhibit_name = exhibit["name"] if exhibit else "MuseBot Exhibit"
    date = slot["date"] if slot else ""

    badge = generate_visit_badge(visitor_name, exhibit_name, date)

    await bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "completed"}}
    )

    return {"id": booking_id, "status": "completed", "badge": badge}