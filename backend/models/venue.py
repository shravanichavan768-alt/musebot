from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.py_object_id import PyObjectId

class Venue(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    type: str  
    slug: str 
    logoUrl: Optional[str] = None
    primaryColor: Optional[str] = "#4F46E5"
    city: Optional[str] = None
    active: bool = True
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True