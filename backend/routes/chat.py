from fastapi import APIRouter,Depends
from pydantic import BaseModel
from services.nlp import parse_booking_intent
from services.conversation import handle_message
from services.auth_dependency import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatMessage(BaseModel):
    message: str

class ConversationMessage(BaseModel):
    
    message: str

@router.post("/parse")
async def parse_message(chat: ChatMessage):
    result = parse_booking_intent(chat.message)
    return result

@router.post("/message")
async def conversation_message(payload: ConversationMessage, current_user: dict = Depends(get_current_user)):
    result = await handle_message(current_user["sub"], payload.message)
    return result