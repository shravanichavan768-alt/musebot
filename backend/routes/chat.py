from fastapi import APIRouter
from pydantic import BaseModel
from services.nlp import parse_booking_intent
from services.conversation import handle_message

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatMessage(BaseModel):
    message: str

class ConversationMessage(BaseModel):
    user_id: str
    message: str

@router.post("/parse")
async def parse_message(chat: ChatMessage):
    result = parse_booking_intent(chat.message)
    return result

@router.post("/message")
async def conversation_message(payload: ConversationMessage):
    result = await handle_message(payload.user_id, payload.message)
    return result