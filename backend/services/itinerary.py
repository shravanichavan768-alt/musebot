import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """You are a museum visit planner. Given a visitor's interest area and 
the exhibit they're visiting, generate a short personalized mini itinerary.

Return ONLY valid JSON in this format:
{
  "plan": ["step 1", "step 2", "step 3", "step 4"],
  "estimated_duration_mins": <int>
}

Keep each step short (under 15 words), practical, and specific to a museum visit.
Include a suggested gallery order and 1-2 "must-see" callouts.
"""

def generate_itinerary(exhibit_name: str, preference: str, adults: int, kids: int) -> dict:
    user_prompt = f"Exhibit: {exhibit_name}\nVisitor interest: {preference}\nGroup: {adults} adults, {kids} kids"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=300,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )
    raw_text = response.choices[0].message.content.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"plan": ["Explore at your own pace and enjoy the visit!"], "estimated_duration_mins": 60}