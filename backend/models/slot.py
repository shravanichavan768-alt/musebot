from pydantic import BaseModel, Field
from typing import Optional
from .py_object_id import PyObjectId

class Slot(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    exhibit: PyObjectId
    date: str        
    startTime: str    
    endTime: str
    capacity: int
    booked: int = 0
    crowdStatus: str = "Quiet"   
    discountPercent: float = 0

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True