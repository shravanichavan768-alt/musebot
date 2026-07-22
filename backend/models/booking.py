from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.py_object_id import PyObjectId

class Itinerary(BaseModel):
    preferences: List[str] = []
    plan: List[str] = []

class Booking(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    venueId: PyObjectId
    user: PyObjectId
    slot: PyObjectId
    adults: int = 0
    kids: int = 0
    totalAmount: float
    status: str = "pending"
    qrCode: Optional[str] = None
    itinerary: Itinerary = Itinerary()
    isGroupBooking: bool = False
    groupType: Optional[str] = None
    groupName: Optional[str] = None
    headcount: Optional[int] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True