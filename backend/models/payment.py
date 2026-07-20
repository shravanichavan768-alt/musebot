from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.py_object_id import PyObjectId

class Payment(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    booking: PyObjectId
    razorpayOrderId: Optional[str] = None
    razorpayPaymentId: Optional[str] = None
    amount: float
    status: str = "created"
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True