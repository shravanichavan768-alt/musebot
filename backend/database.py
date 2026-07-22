import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client["musebot"]

exhibits_collection = db["exhibits"]
slots_collection = db["slots"]
users_collection = db["users"]
bookings_collection = db["bookings"]
payments_collection = db["payments"]
sessions_collection = db["sessions"]
otps_collection = db["otps"]
venues_collection = db["venues"]