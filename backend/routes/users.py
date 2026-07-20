from fastapi import APIRouter
from database import users_collection
from models.user import User

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/")
async def create_user(user: User):
    doc = user.model_dump(by_alias=True, exclude={"id"})
    result = await users_collection.insert_one(doc)
    return {"id": str(result.inserted_id)}