# Intruder Detection System

An AI-powered security system that detects unauthorized access attempts on your Windows system. If a wrong password is entered, it captures the intruder's photo and sends alerts via email and SMS in real-time.

---

## Features

- Monitors failed login attempts (Windows Event ID 4625)
- Captures intruder images using the webcam
- Sends email alerts with the intruder's photo
- Sends SMS notifications via Twilio
- Real-time video streaming via web dashboard

---

## Requirements

- Python 3.9+
- A webcam (for capturing images)
- **Windows** for WMI-based login monitoring (runs on Linux without WMI detection)
- Gmail account for email notifications
- Twilio account for SMS alerts (optional)

---

## Project Structure

```
Intruder_Vision/
├── app.py              # Flask application and monitoring logic
├── config.py           # Configuration (loads from .env)
├── .env.example        # Example environment variables
├── .gitignore
├── requirements.txt
├── static/
│   ├── css/
│   ├── js/
│   └── images/         # Captured images stored here
└── templates/
    └── index.html
```

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/balu-16/Intruder_Vision.git
cd Intruder_Vision
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file from the example:

```bash
cp .env.example .env
```

4. Edit `.env` with your credentials (see `.env.example` for all options).

---

## Configuration

All configuration is via environment variables (or a `.env` file). See `.env.example` for the full list:

| Variable | Default | Description |
|---|---|---|
| `EMAIL_SENDER` | *(required for email)* | Gmail address |
| `EMAIL_PASSWORD` | *(required for email)* | Gmail app password |
| `EMAIL_RECEIVER` | *(required for email)* | Alert recipient address |
| `TWILIO_SID` | *(required for SMS)* | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | *(required for SMS)* | Twilio auth token |
| `TWILIO_PHONE` | *(required for SMS)* | Twilio phone number |
| `OWNER_PHONE` | *(required for SMS)* | Your phone number |
| `ENABLE_WMI_MONITORING` | `true` | Enable Windows login monitoring |
| `ENABLE_EMAIL_ALERTS` | `true` | Enable email alerts |
| `ENABLE_SMS_ALERTS` | `true` | Enable SMS alerts |
| `FLASK_HOST` | `127.0.0.1` | Server bind address |
| `FLASK_PORT` | `5000` | Server port |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |

---

## Usage

### Development

```bash
python app.py
```

### Production (with Gunicorn)

```bash
gunicorn --bind 0.0.0.0:5000 --threads 4 app:app
```

Access the web interface at `http://127.0.0.1:5000`.

---

## Platform Notes

- **Windows**: Full functionality including WMI-based login monitoring (Event ID 4625).
- **Linux/macOS**: Web dashboard, camera streaming, email/SMS alerts all work. WMI monitoring is automatically skipped.

---

## Optional Dependencies

For SMS alerts and Windows monitoring, install the optional packages:

```bash
pip install twilio>=9.0.0    # SMS alerts
pip install WMI>=1.5.1       # Windows login monitoring
pip install pywin32>=306      # Required by WMI
```

---

## Disclaimer

This project is intended for educational and security purposes only. Unauthorized use, monitoring, or surveillance of individuals without consent may be illegal in your jurisdiction. The authors are not liable for any misuse.
