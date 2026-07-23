from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from database import admins_collection, venues_collection
from services.auth import hash_password, verify_password, create_admin_token

router = APIRouter(prefix="/api/admin-auth", tags=["admin-auth"])

class AdminSignup(BaseModel):
    venue_id: str
    username: str
    password: str

class AdminLogin(BaseModel):
    venue_id: str
    username: str
    password: str

@router.post("/signup")
async def admin_signup(payload: AdminSignup):
    venue = await venues_collection.find_one({"_id": ObjectId(payload.venue_id)})
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    existing = await admins_collection.find_one({"venueId": ObjectId(payload.venue_id), "username": payload.username})
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken for this venue")

    doc = {
        "venueId": ObjectId(payload.venue_id),
        "username": payload.username,
        "passwordHash": hash_password(payload.password)
    }
    result = await admins_collection.insert_one(doc)
    return {"id": str(result.inserted_id), "username": payload.username}

@router.post("/login")
async def admin_login(payload: AdminLogin):
    admin = await admins_collection.find_one({
        "venueId": ObjectId(payload.venue_id),
        "username": payload.username
    })
    if not admin or not verify_password(payload.password, admin["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_admin_token(str(admin["_id"]), payload.venue_id, payload.username)
    return {"access_token": token, "token_type": "bearer"}