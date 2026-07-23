from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.py_object_id import PyObjectId

class Admin(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    venueId: PyObjectId
    username: str
    passwordHash: str
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True