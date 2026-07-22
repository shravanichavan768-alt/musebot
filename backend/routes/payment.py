from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.payment import verify_payment_signature
from services.qr_generator import generate_ticket_qr
from services.itinerary import generate_itinerary
from database import bookings_collection, slots_collection, exhibits_collection
from bson import ObjectId

router = APIRouter(prefix="/api/payment", tags=["payment"])

class VerifyPaymentRequest(BaseModel):
    booking_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@router.post("/verify")
async def verify_payment(payload: VerifyPaymentRequest):
    is_valid = verify_payment_signature(
        payload.razorpay_order_id, payload.razorpay_payment_id, payload.razorpay_signature
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    booking = await bookings_collection.find_one({"_id": ObjectId(payload.booking_id)})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    slot = await slots_collection.find_one({"_id": booking["slot"]})
    exhibit = await exhibits_collection.find_one({"_id": slot["exhibit"]}) if slot else None
    exhibit_name = exhibit["name"] if exhibit else "MuseBot Exhibit"
    pref = booking["itinerary"]["preferences"][0] if booking["itinerary"]["preferences"] else "general"

    itinerary_result = generate_itinerary(exhibit_name, pref, booking["adults"], booking["kids"])
    qr_code = generate_ticket_qr(
        payload.booking_id, exhibit_name, slot["date"] if slot else "", booking["adults"], booking["kids"]
    )

    await bookings_collection.update_one(
        {"_id": ObjectId(payload.booking_id)},
        {"$set": {
            "status": "confirmed",
            "qrCode": qr_code,
            "itinerary.plan": itinerary_result["plan"]
        }}
    )

    return {
        "status": "verified",
        "booking_id": payload.booking_id,
        "qr_code": qr_code,
        "itinerary": itinerary_result
    }