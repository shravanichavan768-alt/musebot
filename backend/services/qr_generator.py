import qrcode
import io
import base64
import json

def generate_ticket_qr(booking_id: str, exhibit_name: str, date: str, adults: int, kids: int) -> str:
    
    payload = {
        "booking_id": booking_id,
        "exhibit": exhibit_name,
        "date": date,
        "adults": adults,
        "kids": kids
    }
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(json.dumps(payload))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"