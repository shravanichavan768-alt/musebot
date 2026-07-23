from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.payment import verify_payment_signature
from services.qr_generator import generate_ticket_qr
from services.itinerary import generate_itinerary
from database import bookings_collection, slots_collection, exhibits_collection, users_collection
from bson import ObjectId
from services.email_service import send_ticket_email
from services.translator import translate_from_english

router = APIRouter(prefix="/api/payment", tags=["payment"])

class VerifyPaymentRequest(BaseModel):
    booking_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@router.post("/verify")
async def verify_payment(payload: VerifyPaymentRequest):
    if not ObjectId.is_valid(payload.booking_id):
        raise HTTPException(status_code=400, detail="Invalid booking id")

    booking = await bookings_collection.find_one({"_id": ObjectId(payload.booking_id)})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking["status"] == "confirmed":
        return {
            "status": "already_verified",
            "booking_id": payload.booking_id,
            "qr_code": booking.get("qrCode"),
            "itinerary": {"plan": booking.get("itinerary", {}).get("plan", [])}
        }

    if booking["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Booking cannot be verified (status: {booking['status']})")

    is_valid = verify_payment_signature(
        payload.razorpay_order_id, payload.razorpay_payment_id, payload.razorpay_signature
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    slot = await slots_collection.find_one({"_id": booking["slot"]})
    exhibit = await exhibits_collection.find_one({"_id": slot["exhibit"]}) if slot else None
    exhibit_name = exhibit["name"] if exhibit else "MuseBot Exhibit"
    pref = booking["itinerary"]["preferences"][0] if booking["itinerary"]["preferences"] else "general"

    itinerary_result = generate_itinerary(exhibit_name, pref, booking["adults"], booking["kids"])
    qr_code = generate_ticket_qr(
        payload.booking_id, exhibit_name, slot["date"] if slot else "", booking["adults"], booking["kids"]
    )

    update_result = await bookings_collection.update_one(
        {"_id": ObjectId(payload.booking_id), "status": "pending"},
        {"$set": {
            "status": "confirmed",
            "qrCode": qr_code,
            "razorpayPaymentId": payload.razorpay_payment_id,
            "itinerary.plan": itinerary_result["plan"]
        }}
    )

    if update_result.modified_count == 0:
        fresh = await bookings_collection.find_one({"_id": ObjectId(payload.booking_id)})
        return {
            "status": "already_verified",
            "booking_id": payload.booking_id,
            "qr_code": fresh.get("qrCode"),
            "itinerary": {"plan": fresh.get("itinerary", {}).get("plan", [])}
        }

    user = await users_collection.find_one({"_id": booking["user"]})
    if user and user.get("email"):
        send_ticket_email(
            to_email=user["email"],
            visitor_name=user.get("name", "Visitor"),
            exhibit_name=exhibit_name,
            date=slot["date"] if slot else "",
            qr_code_base64=qr_code,
            itinerary_plan=itinerary_result["plan"]
        )

    plan_text = "\n".join(f"• {step}" for step in itinerary_result["plan"])
    success_message = f"🎉 Payment successful! Your ticket is confirmed.\n\n📍 Your Personalized Visit Plan:\n{plan_text}\n\nHere's your QR code:"

    user_lang = user.get("preferredLanguage", "en") if user else "en"
    if user_lang != "en":
        success_message = translate_from_english(success_message, user_lang)

    return {
        "status": "verified",
        "booking_id": payload.booking_id,
        "qr_code": qr_code,
        "itinerary": itinerary_result,
        "message": success_message
    }

    return {
        "status": "verified",
        "booking_id": payload.booking_id,
        "qr_code": qr_code,
        "itinerary": itinerary_result
    }