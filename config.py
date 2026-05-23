# IntruderVision Configuration

import os
from dotenv import load_dotenv

load_dotenv()

# Email settings
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "")

# Twilio settings
TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE", "")
OWNER_PHONE = os.environ.get("OWNER_PHONE", "")

# Application settings
ENABLE_WMI_MONITORING = os.environ.get("ENABLE_WMI_MONITORING", "true").lower() == "true"
ENABLE_EMAIL_ALERTS = os.environ.get("ENABLE_EMAIL_ALERTS", "true").lower() == "true"
ENABLE_SMS_ALERTS = os.environ.get("ENABLE_SMS_ALERTS", "true").lower() == "true"

# Flask server settings
FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
