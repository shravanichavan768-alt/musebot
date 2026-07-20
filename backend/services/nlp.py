import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """You extract museum ticket booking details from user messages.
Return ONLY valid JSON, no other text, in this exact format:
{
  "intent": "book_ticket" | "check_availability" | "general_query" | "unclear",
  "adults": <int, default 0>,
  "kids": <int, default 0>,
  "exhibit_keyword": "<string or null, e.g. 'dinosaur', 'planetarium'>",
  "date": "<string as user said it, e.g. 'tomorrow', '2026-07-25', or null>",
  "raw_time_hint": "<string or null, e.g. 'evening', 'morning'>"
}

Examples:
"2 adults 1 kid tomorrow for dinosaur exhibit" ->
{"intent": "book_ticket", "adults": 2, "kids": 1, "exhibit_keyword": "dinosaur", "date": "tomorrow", "raw_time_hint": null}

"is the planetarium show open this weekend" ->
{"intent": "check_availability", "adults": 0, "kids": 0, "exhibit_keyword": "planetarium", "date": "this weekend", "raw_time_hint": null}
"""

def parse_booking_intent(user_message: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=300,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )
    raw_text = response.choices[0].message.content.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"intent": "unclear", "adults": 0, "kids": 0, "exhibit_keyword": None, "date": None, "raw_time_hint": None}