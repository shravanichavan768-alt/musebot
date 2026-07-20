from PIL import Image, ImageDraw, ImageFont
import io
import base64
from datetime import datetime

def generate_visit_badge(visitor_name: str, exhibit_name: str, date: str) -> str:
    """
    Generates a shareable 'visit badge' image, returns base64 PNG.
    """
    width, height = 600, 400
    img = Image.new("RGB", (width, height), color="#4F46E5")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 32)
        font_body = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.rectangle([20, 20, width - 20, height - 20], outline="white", width=3)
    draw.text((width / 2, 80), "🏛️ VISIT BADGE", font=font_title, fill="white", anchor="mm")
    draw.text((width / 2, 160), exhibit_name, font=font_body, fill="white", anchor="mm")
    draw.text((width / 2, 200), f"Visited by {visitor_name}", font=font_body, fill="white", anchor="mm")
    draw.text((width / 2, 240), date, font=font_small, fill="#E0E7FF", anchor="mm")
    draw.text((width / 2, 320), "Thanks for visiting MuseBot!", font=font_small, fill="#C7D2FE", anchor="mm")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"