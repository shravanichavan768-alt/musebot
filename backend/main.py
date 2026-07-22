from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import exhibits, slots, bookings, users,chat,payment,auth,venues

app = FastAPI(title="MuseBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(exhibits.router)
app.include_router(slots.router)
app.include_router(bookings.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(payment.router)
app.include_router(auth.router)
app.include_router(venues.router)

@app.get("/")
async def root():
    return {"status": "MuseBot backend running"}