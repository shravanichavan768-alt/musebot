from fastapi import APIRouter, HTTPException
from bson import ObjectId
from database import exhibits_collection
from models.exhibit import Exhibit

router = APIRouter(prefix="/api/exhibits", tags=["exhibits"])

@router.get("/")
async def get_exhibits(venue_id: str = None):
    query = {"active": True}
    if venue_id:
        query["venueId"] = ObjectId(venue_id)
    exhibits = await exhibits_collection.find(query).to_list(100)
    for e in exhibits:
        e["_id"] = str(e["_id"])
        e["venueId"] = str(e["venueId"])
    return exhibits

@router.get("/{exhibit_id}")
async def get_exhibit(exhibit_id: str):
    exhibit = await exhibits_collection.find_one({"_id": ObjectId(exhibit_id)})
    if not exhibit:
        raise HTTPException(status_code=404, detail="Exhibit not found")
    exhibit["_id"] = str(exhibit["_id"])
    exhibit["venueId"] = str(exhibit["venueId"])
    return exhibit

@router.post("/")
async def create_exhibit(exhibit: Exhibit):
    doc = exhibit.model_dump(by_alias=True, exclude={"id"})
    doc["venueId"] = ObjectId(doc["venueId"])
    result = await exhibits_collection.insert_one(doc)
    return {"id": str(result.inserted_id)}