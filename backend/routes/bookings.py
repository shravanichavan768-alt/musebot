from fastapi import APIRouter, HTTPException
from bson import ObjectId
from database import bookings_collection,slots_collection, users_collection, exhibits_collection
from models.booking import Booking
from services.crowd_meter import calculate_crowd_status
from services.souvenir import generate_visit_badge
from services.group_pricing import calculate_group_price
from pydantic import BaseModel as PydanticModel
from services.qr_generator import generate_ticket_qr

router = APIRouter(prefix="/api/bookings", tags=["bookings"])
class GroupBookingRequest(PydanticModel):
    user_id: str
    slot_id: str
    headcount: int
    group_type: str  
    group_name: str

@router.post("/")
async def create_booking(booking: Booking):
    slot = await slots_collection.find_one({"_id": ObjectId(booking.slot)})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    requested = booking.adults + booking.kids
    remaining = slot["capacity"] - slot["booked"]
    if requested > remaining:
        raise HTTPException(status_code=400, detail=f"Only {remaining} seats left in this slot")

    
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


@router.post("/group")
async def create_group_booking(payload: GroupBookingRequest):
    slot = await slots_collection.find_one({"_id": ObjectId(payload.slot_id)})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    remaining = slot["capacity"] - slot["booked"]
    if payload.headcount > remaining:
        raise HTTPException(status_code=400, detail=f"Only {remaining} seats left in this slot")

    is_school = payload.group_type == "school"
    pricing = calculate_group_price(payload.headcount, is_school)

    doc = {
        "user": ObjectId(payload.user_id),
        "slot": ObjectId(payload.slot_id),
        "adults": payload.headcount,
        "kids": 0,
        "totalAmount": pricing["final_amount"],
        "status": "confirmed",
        "itinerary": {"preferences": [], "plan": []},
        "isGroupBooking": True,
        "groupType": payload.group_type,
        "groupName": payload.group_name,
        "headcount": payload.headcount
    }

    result = await bookings_collection.insert_one(doc)
    booking_id = str(result.inserted_id)

    await slots_collection.update_one(
        {"_id": ObjectId(payload.slot_id)},
        {"$inc": {"booked": payload.headcount}}
    )

    
    qr_code = generate_ticket_qr(booking_id, payload.group_name, slot["date"], payload.headcount, 0)
    await bookings_collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"qrCode": qr_code}}
    )

    return {
        "booking_id": booking_id,
        "group_name": payload.group_name,
        "headcount": payload.headcount,
        "pricing": pricing,
        "qr_code": qr_code
    }