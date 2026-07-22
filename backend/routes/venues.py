from fastapi import APIRouter, HTTPException
from bson import ObjectId
from database import venues_collection
from models.venue import Venue

router = APIRouter(prefix="/api/venues", tags=["venues"])

@router.get("/")
async def get_venues():
    venues = await venues_collection.find({"active": True}).to_list(100)
    for v in venues:
        v["_id"] = str(v["_id"])
    return venues

@router.get("/slug/{slug}")
async def get_venue_by_slug(slug: str):
    venue = await venues_collection.find_one({"slug": slug})
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    venue["_id"] = str(venue["_id"])
    return venue

@router.post("/")
async def create_venue(venue: Venue):
    existing = await venues_collection.find_one({"slug": venue.slug})
    if existing:
        raise HTTPException(status_code=409, detail="Venue slug already exists")
    doc = venue.model_dump(by_alias=True, exclude={"id"})
    result = await venues_collection.insert_one(doc)
    return {"id": str(result.inserted_id)}