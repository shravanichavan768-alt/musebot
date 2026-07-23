from datetime import datetime, timedelta
from services.nlp import parse_booking_intent
from database import exhibits_collection, slots_collection, users_collection, bookings_collection, sessions_collection,venues_collection
from services.crowd_meter import calculate_crowd_status
from services.payment import create_payment_order,create_refund
from services.qr_generator import generate_ticket_qr
from services.itinerary import generate_itinerary
from services.translator import detect_language, translate_to_english, translate_from_english
from services.cancellation_policy import calculate_refund_amount
from bson import ObjectId

PRICE_PER_ADULT = 200
PRICE_PER_KID = 100

DEFAULT_SESSION = {
    "stage": "greeting",
    "language": "en",
    "booking_draft": {},
    "available_slots": [],
    "pending_order": None
}

async def get_session(user_id: str) -> dict:
    session = await sessions_collection.find_one({"user_id": user_id})
    if not session:
        session = {"user_id": user_id, **DEFAULT_SESSION, "updatedAt": datetime.utcnow()}
        await sessions_collection.insert_one(session)
    return session

async def save_session(user_id: str, session: dict):
    session["updatedAt"] = datetime.utcnow()
    session.pop("_id", None)  
    await sessions_collection.update_one(
        {"user_id": user_id},
        {"$set": session},
        upsert=True
    )


async def handle_message(user_id: str, message: str,venue_id:str) -> dict:
    session = await get_session(user_id)
    session["venueId"] = venue_id  

    if session["stage"] == "greeting" or session.get("language") == "en":
        detected = detect_language(message)
        if detected != "en" and detected != session.get("language"):
            session["language"] = detected
            await users_collection.update_one(
                {"telegramChatId": user_id},
                {"$set": {"preferredLanguage": detected}}
            )

    if session["language"] != "en":
        message = translate_to_english(message, session["language"])

    result = await _process_stage(user_id, session, message)

    await save_session(user_id, session)

    if session["language"] != "en" and "reply" in result:
        result["reply"] = translate_from_english(result["reply"], session["language"])

    return result


async def _process_stage(user_id: str, session: dict, message: str) -> dict:
    stage = session["stage"]
    venue_id = session.get("venueId")

    if stage == "greeting":
        session["stage"] = "awaiting_intent"
        venue = await venues_collection.find_one({"_id": ObjectId(session.get("venueId"))}) if session.get("venueId") else None
        venue_name = venue["name"] if venue else "our venue"
        return {
            "reply": f"Welcome to {venue_name}! Fill in the details below to book your tickets.",
            "stage": session["stage"],
            "show_booking_form": True
        }
    
    if stage == "awaiting_intent":
        parsed = parse_booking_intent(message)
        if parsed["intent"] != "book_ticket":
            return {"reply": "I can help you book tickets — try telling me headcount, exhibit, and date.", "stage": stage}

        keyword = (parsed.get("exhibit_keyword") or "").lower()
        exhibit = await exhibits_collection.find_one({"name": {"$regex": keyword, "$options": "i"},"venueId": ObjectId(venue_id)}) if keyword else None

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

        venue = await venues_collection.find_one({"_id": ObjectId(session.get("venueId"))}) if session.get("venueId") else None
        venue_type = venue["type"] if venue else "museum"

        pref_options = {
            "museum": "history / art / science / kids",
            "national_park": "wildlife / trekking / photography / kids",
            "heritage_site": "architecture / history / photography / kids",
            "science_center": "space / robotics / physics / kids"
        }
        options_text = pref_options.get(venue_type, "history / art / science / kids")

        return {
            "reply": f"Nice choice! Quick question to build your visit plan — what are you most interested in? ({options_text})",
            "stage": session["stage"]
        }

    if stage == "awaiting_itinerary_pref":
        session["booking_draft"]["itinerary_pref"] = message.lower()
        session["stage"] = "awaiting_email"
        return {
            "reply": "Almost done! What's your email address? We'll send your ticket there too.",
            "stage": session["stage"]
        }

    if stage == "awaiting_email":
        email = message.strip()
        if "@" not in email or "." not in email:
            return {"reply": "That doesn't look like a valid email. Please enter a valid email address.", "stage": stage}

        session["booking_draft"]["email"] = email
        session["stage"] = "awaiting_payment"
        draft = session["booking_draft"]
        return {
            "reply": f"Great! Here's your booking summary:\n- {draft['exhibit_name']}\n- {draft['adults']} adults, {draft['kids']} kids\n- Date: {draft['date']}\n- Email: {email}\n\nReady to pay? (yes/no)",
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
                    "email": draft.get("email"),
                    "channel": "web",
                    "telegramChatId": user_id,
                    "preferredLanguage": session["language"]
                })
                user_mongo_id = user_result.inserted_id
            else:
                user_mongo_id = user_doc["_id"]
                await users_collection.update_one(
                    {"_id": user_mongo_id},
                    {"$set": {"email": draft.get("email")}}
                )

           
            booking_result = await bookings_collection.insert_one({
                "user": user_mongo_id,
                "venueId": ObjectId(venue_id),
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

async def handle_message(user_id: str, message: str, venue_id: str) -> dict:
    session = await get_session(user_id)
    session["venueId"] = venue_id

    if session["stage"] == "greeting" or session.get("language") == "en":
        detected = detect_language(message)
        if detected != "en":
            session["language"] = detected

    translated_message = message
    if session["language"] != "en":
        translated_message = translate_to_english(message, session["language"])

    # Handle cancellation as a global command, works from any stage
    if translated_message.strip().lower() in ("cancel", "cancel booking", "cancel my booking"):
        result = await _handle_cancel_request(user_id)
        await save_session(user_id, session)
        if session["language"] != "en" and "reply" in result:
            result["reply"] = translate_from_english(result["reply"], session["language"])
        return result

    if translated_message.strip().lower().startswith("rate "):
        try:
            rating = int(translated_message.strip().split(" ")[1])
            if not (1 <= rating <= 5):
                raise ValueError()
        except (ValueError, IndexError):
            result = {"reply": "Please rate like this: 'rate 5' (1-5 stars)", "stage": session["stage"]}
            await save_session(user_id, session)
            if session["language"] != "en" and "reply" in result:
                result["reply"] = translate_from_english(result["reply"], session["language"])
            return result

        user_doc = await users_collection.find_one({"telegramChatId": user_id})
        if not user_doc:
            result = {"reply": "No booking found to rate.", "stage": session["stage"]}
        else:
            booking = await bookings_collection.find_one(
                {"user": user_doc["_id"], "status": {"$in": ["completed", "checked_in", "confirmed"]}},
                sort=[("createdAt", -1)]
            )
            if not booking:
                result = {"reply": "No booking found to rate.", "stage": session["stage"]}
            else:
                await bookings_collection.update_one(
                    {"_id": booking["_id"]},
                    {"$set": {"feedbackRating": rating}}
                )
                result = {"reply": f"Thanks for rating us {rating}⭐! We appreciate your feedback.", "stage": session["stage"]}

        await save_session(user_id, session)
        if session["language"] != "en" and "reply" in result:
            result["reply"] = translate_from_english(result["reply"], session["language"])
        return result

    result = await _process_stage(user_id, session, translated_message)

    await save_session(user_id, session)

    if session["language"] != "en" and "reply" in result:
        result["reply"] = translate_from_english(result["reply"], session["language"])

    return result


async def _handle_cancel_request(user_id: str) -> dict:
    user_doc = await users_collection.find_one({"telegramChatId": user_id})
    if not user_doc:
        return {"reply": "You don't have any bookings to cancel.", "stage": "idle"}

    booking = await bookings_collection.find_one(
        {"user": user_doc["_id"], "status": "confirmed"},
        sort=[("createdAt", -1)]
    )
    if not booking:
        return {"reply": "You don't have any active confirmed bookings to cancel.", "stage": "idle"}

    slot = await slots_collection.find_one({"_id": booking["slot"]})
    exhibit = await exhibits_collection.find_one({"_id": slot["exhibit"]}) if slot else None
    exhibit_name = exhibit["name"] if exhibit else "your booking"
    visit_date = slot["date"] if slot else None

    policy_result = calculate_refund_amount(booking["totalAmount"], visit_date)

    refund_info = None
    if policy_result["eligible"] and policy_result["refund_amount"] > 0:
        payment_id = booking.get("razorpayPaymentId")
        if payment_id and not payment_id.startswith("pay_mock"):
            try:
                refund_info = create_refund(payment_id, policy_result["refund_amount"])
            except Exception:
                pass

    if slot:
        headcount = booking["adults"] + booking["kids"]
        await slots_collection.update_one(
            {"_id": booking["slot"]},
            {"$inc": {"booked": -headcount}}
        )

    await bookings_collection.update_one(
        {"_id": booking["_id"]},
        {"$set": {
            "status": "cancelled",
            "refundAmount": policy_result["refund_amount"],
            "refundReason": policy_result["reason"]
        }}
    )

    if policy_result["eligible"]:
        reply = f"Your booking for {exhibit_name} has been cancelled. Refund of ₹{policy_result['refund_amount']} has been initiated. {policy_result['reason']}"
    else:
        reply = f"Your booking for {exhibit_name} has been cancelled. {policy_result['reason']}"

    return {"reply": reply, "stage": "idle", "booking_id": str(booking["_id"])}