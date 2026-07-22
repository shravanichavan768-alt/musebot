from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from services.nlp import parse_booking_intent
from services.conversation import handle_message
from services.auth_dependency import get_current_user
from database import users_collection

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatMessage(BaseModel):
    message: str

class ConversationMessage(BaseModel):
    
    message: str
    venue_id: str

class SetLanguageRequest(BaseModel):
    language: str


@router.post("/parse")
async def parse_message(chat: ChatMessage):
    result = parse_booking_intent(chat.message)
    return result

@router.post("/message")
async def conversation_message(payload: ConversationMessage, current_user: dict = Depends(get_current_user)):
    result = await handle_message(current_user["sub"], payload.message, payload.venue_id)
    return result

@router.post("/set-language")
async def set_language(payload: SetLanguageRequest, current_user: dict = Depends(get_current_user)):
    from services.translator import SUPPORTED_LANGUAGES
    if payload.language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")

    from services.conversation import get_session, save_session
    session = await get_session(current_user["sub"])
    session["language"] = payload.language
    await save_session(current_user["sub"], session)

    await users_collection.update_one(
        {"telegramChatId": current_user["sub"]},
        {"$set": {"preferredLanguage": payload.language}}
    )
    return {"language": payload.language}