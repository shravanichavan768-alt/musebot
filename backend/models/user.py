from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from models.py_object_id import PyObjectId

class User(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    channel: str = "web"   
    telegramChatId: Optional[str] = None
    preferredLanguage: str = "en"
    createdAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True