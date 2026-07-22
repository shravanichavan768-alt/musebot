from datetime import datetime, timedelta
from services.nlp import parse_booking_intent
from database import exhibits_collection, slots_collection, users_collection, bookings_collection
from services.crowd_meter import calculate_crowd_status
from services.payment import create_payment_order
from services.qr_generator import generate_ticket_qr
from services.itinerary import generate_itinerary
from services.translator import detect_language, translate_to_english, translate_from_english
from bson import ObjectId

sessions = {}

PRICE_PER_ADULT = 200
PRICE_PER_KID = 100

def get_session(user_id: str) -> dict:
    if user_id not in sessions:
        sessions[user_id] = {
            "stage": "greeting",
            "language": "en",
            "booking_draft": {}
        }
    return sessions[user_id]


async def handle_message(user_id: str, message: str) -> dict:
    session = get_session(user_id)

    
    if session["stage"] == "greeting" or session.get("language") == "en":
        detected = detect_language(message)
        if detected != "en":
            session["language"] = detected

    
    if session["language"] != "en":
        message = translate_to_english(message, session["language"])

    result = await _process_stage(user_id, session, message)

    
    if session["language"] != "en" and "reply" in result:
        result["reply"] = translate_from_english(result["reply"], session["language"])

    return result


async def _process_stage(user_id: str, session: dict, message: str) -> dict:
    stage = session["stage"]

    if stage == "greeting":
        session["stage"] = "awaiting_intent"
        return {
            "reply": "Welcome to MuseBot! I can help you book tickets. What would you like to visit, and when? (e.g. '2 adults 1 kid tomorrow for dinosaur exhibit')",
            "stage": session["stage"]
        }

    if stage == "awaiting_intent":
        parsed = parse_booking_intent(message)
        if parsed["intent"] != "book_ticket":
            return {"reply": "I can help you book tickets — try telling me headcount, exhibit, and date.", "stage": stage}

        keyword = (parsed.get("exhibit_keyword") or "").lower()
        exhibit = await exhibits_collection.find_one({"name": {"$regex": keyword, "$options": "i"}}) if keyword else None

        if not exhibit:
            return {"reply": f"I couldn't find an exhibit matching '{keyword}'. Could you rephrase?", "stage": stage}

        session["booking_draft"] = {
            "exhibit_id": str(exhibit["_id"]),
            "exhibit_name": exhibit["name"],
            "adults": parsed["adults"],
            "kids": parsed["kids"],
            "date_hint": parsed["date"]
        }
        session["stage"] = "awaiting_slot_confirm"

        date_str = parsed["date"]
        if date_str and "tomorrow" in date_str.lower():
            date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        session["booking_draft"]["date"] = date_str

        slots = await slots_collection.find({
            "exhibit": exhibit["_id"],
            "date": date_str
        }).to_list(20)

        if not slots:
            return {"reply": f"No slots found for {exhibit['name']} on {date_str}. Try another date?", "stage": stage}

        slot_lines = []
        for s in slots:
            crowd = calculate_crowd_status(s["capacity"], s["booked"])
            line = f"{s['startTime']}-{s['endTime']} | {crowd['status']}"
            if crowd["discountPercent"] > 0:
                line += f" | {crowd['discountPercent']}% off!"
            slot_lines.append(line)

        session["available_slots"] = [str(s["_id"]) for s in slots]

        return {
            "reply": f"Found slots for {exhibit['name']} on {date_str}:\n" + "\n".join(slot_lines) + "\n\nWhich time works for you?",
            "stage": session["stage"]
        }

    if stage == "awaiting_slot_confirm":
        slots = await slots_collection.find(
            {"_id": {"$in": [ObjectId(sid) for sid in session["available_slots"]]}}
        ).to_list(20)
        chosen = next((s for s in slots if s["startTime"] in message), None)
        if not chosen:
            return {"reply": "Please enter the time exactly as shown, e.g. '10:00'.", "stage": stage}

        session["booking_draft"]["slot_id"] = str(chosen["_id"])
        session["stage"] = "awaiting_itinerary_pref"
        return {
            "reply": "Nice choice! Quick question to build your visit plan — what are you most interested in? (history / art / science / kids)",
            "stage": session["stage"]
        }

    if stage == "awaiting_itinerary_pref":
        session["booking_draft"]["itinerary_pref"] = message.lower()
        session["stage"] = "awaiting_payment"
        draft = session["booking_draft"]
        return {
            "reply": f"Great! Here's your booking summary:\n- {draft['exhibit_name']}\n- {draft['adults']} adults, {draft['kids']} kids\n- Date: {draft['date']}\n\nReady to pay? (yes/no)",
            "stage": session["stage"]
        }

    if stage == "awaiting_payment":
        if "yes" in message.lower():
            draft = session["booking_draft"]
            amount = draft["adults"] * PRICE_PER_ADULT + draft["kids"] * PRICE_PER_KID

            
            user_doc = await users_collection.find_one({"telegramChatId": user_id})
            if not user_doc:
                user_result = await users_collection.insert_one({
                    "name": user_id,
                    "channel": "web",
                    "telegramChatId": user_id,
                    "preferredLanguage": session["language"]
                })
                user_mongo_id = user_result.inserted_id
            else:
                user_mongo_id = user_doc["_id"]

           
            booking_result = await bookings_collection.insert_one({
                "user": user_mongo_id,
                "slot": ObjectId(draft["slot_id"]),
                "adults": draft["adults"],
                "kids": draft["kids"],
                "totalAmount": amount,
                "status": "pending",
                "itinerary": {"preferences": [draft["itinerary_pref"]], "plan": []}
            })
            booking_id = str(booking_result.inserted_id)
            session["booking_draft"]["booking_id"] = booking_id

            order = create_payment_order(amount)
            session["stage"] = "payment_pending"

            return {
                "reply": f"Order created for ₹{amount}. Complete payment in the popup...",
                "stage": session["stage"],
                "action": "initiate_payment",
                "order": order,
                "booking_id": booking_id
            }
        return {"reply": "No worries, let me know when you're ready.", "stage": stage}

    if stage == "payment_pending":
        
        return {
            "reply": "Please complete the payment in the popup window. Once done, your ticket will be generated automatically.",
            "stage": "payment_pending"
        }