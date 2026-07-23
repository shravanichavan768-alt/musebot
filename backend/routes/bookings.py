from fastapi import APIRouter, HTTPException,Depends
from bson import ObjectId
from typing import Optional
from database import bookings_collection,slots_collection, users_collection, exhibits_collection
from models.booking import Booking
from services.crowd_meter import calculate_crowd_status
from services.souvenir import generate_visit_badge
from services.group_pricing import calculate_group_price
from pydantic import BaseModel as PydanticModel
from services.qr_generator import generate_ticket_qr
from pydantic import BaseModel as PydanticModel
from services.cancellation_policy import calculate_refund_amount
from services.payment import create_refund
from services.auth_dependency import get_current_user
import json as json_lib

router = APIRouter(prefix="/api/bookings", tags=["bookings"])
class GroupBookingRequest(PydanticModel):
    user_id: str
    slot_id: str
    headcount: int
    group_type: str  
    group_name: str

class QRVerifyRequest(PydanticModel):
    qr_payload: str 

class FeedbackRequest(PydanticModel):
    rating: int  
    comment: Optional[str] = None

@router.post("/")
async def create_booking(booking: Booking, current_user: dict = Depends(get_current_user)):
    slot = await slots_collection.find_one({"_id": ObjectId(booking.slot)})
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    requested = booking.adults + booking.kids
    remaining = slot["capacity"] - slot["booked"]
    if requested > remaining:
        raise HTTPException(status_code=400, detail=f"Only {remaining} seats left in this slot")

    doc = booking.model_dump(by_alias=True, exclude={"id"})
    doc["user"] = ObjectId(current_user["sub"])  
    doc["slot"] = ObjectId(booking.slot)
    result = await bookings_collection.insert_one(doc)

    await slots_collection.update_one(
        {"_id": ObjectId(booking.slot)},
        {"$inc": {"booked": requested}}
    )

    return {"id": str(result.inserted_id), "status": "pending"}

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

    return {"id": booking_id, "status": "completed", "badge": badge, "prompt_feedback": True}


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

@router.post("/verify-qr")
async def verify_qr(payload: QRVerifyRequest):
    try:
        data = json_lib.loads(payload.qr_payload)
        booking_id = data.get("booking_id")
    except (json_lib.JSONDecodeError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid QR payload")

    if not booking_id or not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=400, detail="Invalid booking reference")

    booking = await bookings_collection.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if booking["status"] == "checked_in":
        raise HTTPException(status_code=409, detail="Ticket already used for entry")
    if booking["status"] == "completed":
        raise HTTPException(status_code=409, detail="Visit already completed")
    if booking["status"] != "confirmed":
        raise HTTPException(status_code=400, detail=f"Ticket not valid for entry (status: {booking['status']})")

    await bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "checked_in"}}
    )

    return {
        "valid": True,
        "booking_id": booking_id,
        "adults": booking["adults"],
        "kids": booking["kids"],
        "status": "checked_in"
    }

@router.post("/{booking_id}/cancel")
async def cancel_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=400, detail="Invalid booking id")

    booking = await bookings_collection.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if str(booking["user"]) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="You can only cancel your own bookings")
                            
    if booking["status"] in ("cancelled", "checked_in", "completed"):
        raise HTTPException(status_code=409, detail=f"Booking cannot be cancelled (status: {booking['status']})")

    if booking["status"] != "confirmed":
        raise HTTPException(status_code=400, detail="Only confirmed bookings can be cancelled")

    slot = await slots_collection.find_one({"_id": booking["slot"]})
    visit_date = slot["date"] if slot else None

    policy_result = calculate_refund_amount(booking["totalAmount"], visit_date)

    refund_info = None
    if policy_result["eligible"] and policy_result["refund_amount"] > 0:
        payment_id = booking.get("razorpayPaymentId")
        if payment_id and not payment_id.startswith("pay_mock"):
            try:
                refund_info = create_refund(payment_id, policy_result["refund_amount"])
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Refund failed: {str(e)}")

    
    if slot:
        headcount = booking["adults"] + booking["kids"]
        await slots_collection.update_one(
            {"_id": booking["slot"]},
            {"$inc": {"booked": -headcount}}
        )

    await bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {
            "status": "cancelled",
            "refundAmount": policy_result["refund_amount"],
            "refundReason": policy_result["reason"]
        }}
    )

    return {
        "booking_id": booking_id,
        "status": "cancelled",
        "refund_eligible": policy_result["eligible"],
        "refund_amount": policy_result["refund_amount"],
        "refund_reason": policy_result["reason"],
        "refund_details": refund_info
    }

@router.post("/{booking_id}/feedback")
async def submit_feedback(booking_id: str, payload: FeedbackRequest):
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(status_code=400, detail="Invalid booking id")
    if not (1 <= payload.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    result = await bookings_collection.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"feedbackRating": payload.rating, "feedbackComment": payload.comment}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")

    return {"booking_id": booking_id, "rating": payload.rating}