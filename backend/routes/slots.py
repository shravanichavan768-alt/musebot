from fastapi import APIRouter, HTTPException
from bson import ObjectId
from database import slots_collection
from models.slot import Slot
from services.crowd_meter import calculate_crowd_status

router = APIRouter(prefix="/api/slots", tags=["slots"])

@router.get("/")
async def get_slots(exhibit_id: str = None, date: str = None):
    query = {}
    if exhibit_id:
        query["exhibit"] = ObjectId(exhibit_id)
    if date:
        query["date"] = date
    slots = await slots_collection.find(query).to_list(200)
    for s in slots:
        s["_id"] = str(s["_id"])
        s["exhibit"] = str(s["exhibit"])
        crowd = calculate_crowd_status(s["capacity"], s["booked"])
        s["crowdStatus"] = crowd["status"]
        s["discountPercent"] = crowd["discountPercent"]
    return slots

@router.post("/")
async def create_slot(slot: Slot):
    doc = slot.model_dump(by_alias=True, exclude={"id"})
    doc["exhibit"] = ObjectId(doc["exhibit"])
    result = await slots_collection.insert_one(doc)
    return {"id": str(result.inserted_id)}