import cv2
import smtplib
import time
import wmi
from email.message import EmailMessage
from twilio.rest import Client  # Twilio for SMS

# Email credentials
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_email_password"
EMAIL_RECEIVER = "receiver_email@gmail.com"

# Twilio credentials
TWILIO_SID = "your_twilio_sid"
TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
TWILIO_PHONE = "+1234567890"  # Your Twilio phone number
OWNER_PHONE = "+0987654321"   # Your phone number to receive SMS

# Function to capture intruder's photo
def capture_intruder_photo():
    cam = cv2.VideoCapture(0)

    # Set higher resolution (if supported)
    # cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    ret, frame = cam.read()
    if ret:
        img_path = "intruder.jpg"
        cv2.imwrite(img_path, frame)
    cam.release()
    return img_path

# Function to send alert email
def send_alert_email(image_path):
    msg = EmailMessage()
    msg["Subject"] = "⚠️ Windows Intruder Alert!"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content("A wrong password attempt was detected on your Windows system.")

    with open(image_path, "rb") as img:
        msg.add_attachment(img.read(), maintype="image", subtype="jpeg", filename="intruder.jpg")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

# Function to send SMS alert
def send_sms_alert():
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body="⚠️ Intruder Alert: A wrong password attempt was detected on your Windows system!",
        from_=TWILIO_PHONE,
        to=OWNER_PHONE
    )
    print(f"📩 SMS Sent! Message SID: {message.sid}")

# Function to monitor Windows login attempts
def monitor_windows_logins():
    c = wmi.WMI()
    watcher = c.Win32_NTLogEvent.watch_for("creation", EventCode=4625)  # 4625 = Failed login event
    while True:
        print("Monitoring Windows login attempts...")
        watcher()
        print("❌ Wrong password attempt detected!")
        image_path = capture_intruder_photo()
        send_alert_email(image_path)
        send_sms_alert()
        print("📩 Email & SMS Alert Sent!")
        time.sleep(2)

if __name__ == "__main__":
    monitor_windows_logins()
