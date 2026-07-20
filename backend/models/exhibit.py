from pydantic import BaseModel, Field
from typing import Optional
from models.py_object_id import PyObjectId

class Exhibit(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    type: str  # general | special | guided_tour | planetarium
    description: Optional[str] = None
    basePrice: float
    category: str  # history | art | science | kids
    active: bool = True

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True