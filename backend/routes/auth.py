from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from database import users_collection, otps_collection
from services.auth import generate_otp, create_access_token
from services.email_service import send_otp_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

class RequestOtp(BaseModel):
    email: EmailStr

class VerifyOtp(BaseModel):
    email: EmailStr
    otp: str

@router.post("/request-otp")
async def request_otp(payload: RequestOtp):
    otp = generate_otp()
    await otps_collection.update_one(
        {"email": payload.email},
        {"$set": {"otp": otp, "expiresAt": datetime.utcnow() + timedelta(minutes=10)}},
        upsert=True
    )
    result = send_otp_email(payload.email, otp)
    if not result["sent"]:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
    return {"message": "OTP sent to your email"}

@router.post("/verify-otp")
async def verify_otp(payload: VerifyOtp):
    record = await otps_collection.find_one({"email": payload.email})
    if not record:
        raise HTTPException(status_code=400, detail="No OTP requested for this email")
    if record["expiresAt"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    if record["otp"] != payload.otp:
        raise HTTPException(status_code=400, detail="Incorrect OTP")

   
    user = await users_collection.find_one({"email": payload.email})
    if not user:
        result = await users_collection.insert_one({
            "email": payload.email,
            "name": payload.email.split("@")[0],
            "channel": "web",
            "preferredLanguage": "en"
        })
        user_id = str(result.inserted_id)
    else:
        user_id = str(user["_id"])

    await otps_collection.delete_one({"email": payload.email})

    token = create_access_token(user_id, payload.email)
    return {"access_token": token, "token_type": "bearer", "user_id": user_id}