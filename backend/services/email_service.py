import os
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

def send_ticket_email(to_email: str, visitor_name: str, exhibit_name: str, date: str, qr_code_base64: str, itinerary_plan: list):
    if not to_email:
        return {"sent": False, "reason": "No email provided"}

    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

    msg = MIMEMultipart("related")
    msg["Subject"] = f"Your MuseBot Ticket - {exhibit_name}"
    msg["From"] = sender_email
    msg["To"] = to_email

    plan_html = "".join(f"<li>{step}</li>" for step in itinerary_plan)

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #4F46E5;">🏛️ Your MuseBot Ticket</h2>
        <p>Hi {visitor_name},</p>
        <p>Your ticket for <strong>{exhibit_name}</strong> on <strong>{date}</strong> is confirmed!</p>
        <h3>Your Visit Plan:</h3>
        <ul>{plan_html}</ul>
        <p>Show this QR code at entry:</p>
        <img src="cid:qrcode" width="200" />
        <p style="color: #888; font-size: 12px;">Thanks for booking with MuseBot!</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(html_body, "html"))

    
    qr_base64_data = qr_code_base64.split(",")[1] if "," in qr_code_base64 else qr_code_base64
    qr_bytes = base64.b64decode(qr_base64_data)
    qr_image = MIMEImage(qr_bytes)
    qr_image.add_header("Content-ID", "<qrcode>")
    msg.attach(qr_image)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "reason": str(e)}

def send_otp_email(to_email: str, otp: str):
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

    msg = MIMEMultipart()
    msg["Subject"] = "Your MuseBot Login Code"
    msg["From"] = sender_email
    msg["To"] = to_email

    body = f"""
    <html><body style="font-family: Arial, sans-serif;">
      <h2 style="color: #4F46E5;">Your MuseBot login code</h2>
      <p>Enter this code to continue:</p>
      <h1 style="letter-spacing: 4px;">{otp}</h1>
      <p style="color: #888; font-size: 12px;">This code expires in 10 minutes.</p>
    </body></html>
    """
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "reason": str(e)}