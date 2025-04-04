import os
import cv2
import smtplib
import time
import logging
import threading
import random
from email.message import EmailMessage
from flask import Flask, render_template, jsonify, Response, request
from datetime import datetime
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import configuration
try:
    import config
    logger.info("Configuration loaded successfully")
except ImportError:
    logger.error("Failed to import configuration. Using default values.")

    class config:
        EMAIL_SENDER = "example@gmail.com"
        EMAIL_PASSWORD = "password"
        EMAIL_RECEIVER = "example@gmail.com"
        TWILIO_SID = "your_twilio_sid"
        TWILIO_AUTH_TOKEN = "your_twilio_auth_token"
        TWILIO_PHONE = "+1234567890"
        OWNER_PHONE = "+1234567890"
        ENABLE_WMI_MONITORING = False
        ENABLE_EMAIL_ALERTS = False
        ENABLE_SMS_ALERTS = False
        FLASK_HOST = '127.0.0.1'
        FLASK_PORT = 5000
        FLASK_DEBUG = True

# Import optional dependencies
wmi_available = False
twilio_available = False

if config.ENABLE_WMI_MONITORING:
    try:
        import wmi
        wmi_available = True
        logger.info("WMI module imported successfully")
    except ImportError:
        logger.error(
            "Failed to import WMI module. WMI monitoring will be disabled.")
        config.ENABLE_WMI_MONITORING = False

if config.ENABLE_SMS_ALERTS:
    try:
        from twilio.rest import Client
        twilio_available = True
        logger.info("Twilio module imported successfully")
    except ImportError:
        logger.error(
            "Failed to import Twilio module. SMS alerts will be disabled.")
        config.ENABLE_SMS_ALERTS = False

app = Flask(__name__)

# Global variables
monitoring_active = False
monitoring_thread = None
alerts_history = []
camera = None
stream_active = False
stream_thread = None
latest_frame = None

# Function to capture image


def capture_photo():
    global camera, latest_frame
    try:
        # Use latest frame if available and streaming is active
        if latest_frame is not None and stream_active:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_path = f"static/images/capture_{timestamp}.jpg"
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            cv2.imwrite(img_path, latest_frame)
            return img_path

        # Initialize camera if needed
        if camera is None:
            camera = cv2.VideoCapture(0)
            time.sleep(1)

        ret, frame = camera.read()
        if ret:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_path = f"static/images/capture_{timestamp}.jpg"
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            cv2.imwrite(img_path, frame)

            if not stream_active:
                camera.release()
                camera = None

            return img_path
        return None
    except Exception as e:
        logger.error(f"Error capturing photo: {str(e)}")
        return None

# Function to send alert email


def send_alert_email(image_path):
    if not config.ENABLE_EMAIL_ALERTS:
        logger.info("Email alerts are disabled")
        return False

    try:
        logger.info(f"Sending email alert with image: {image_path}")
        msg = EmailMessage()
        msg["Subject"] = "⚠️ Windows Intruder Alert!"
        msg["From"] = config.EMAIL_SENDER
        msg["To"] = config.EMAIL_RECEIVER
        msg.set_content(
            "A wrong password attempt was detected on your Windows system.")

        with open(image_path, "rb") as img:
            img_data = img.read()
            msg.add_attachment(img_data, maintype="image",
                               subtype="jpeg", filename=os.path.basename(image_path))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info("Email sent successfully")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

# Function to send SMS alert


def send_sms_alert():
    if not config.ENABLE_SMS_ALERTS or not twilio_available:
        logger.info("SMS alerts are disabled or Twilio is not available")
        return None

    try:
        logger.info("Sending SMS alert")
        client = Client(config.TWILIO_SID, config.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body="⚠️ Intruder Alert: A wrong password attempt was detected on your Windows system!",
            from_=config.TWILIO_PHONE,
            to=config.OWNER_PHONE
        )
        logger.info(f"SMS sent with SID: {message.sid}")
        return message.sid
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return None

# Function for testing wrong password


def simulate_wrong_password():
    try:
        # Capture image
        image_path = capture_photo()

        if image_path:
            timestamp = datetime.now()

            # Send alerts
            email_sent = send_alert_email(
                image_path) if config.ENABLE_EMAIL_ALERTS else False
            sms_sid = send_sms_alert() if config.ENABLE_SMS_ALERTS else None

            # Record alert in history
            alert_record = {
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "image_path": image_path,
                "email_sent": email_sent,
                "sms_sid": sms_sid,
                "message": "Wrong password detected!"
            }
            alerts_history.insert(0, alert_record)  # Add at the beginning
            logger.info("Wrong password alert recorded in history")
            return True
        else:
            logger.error("Failed to capture image for wrong password alert")
            return False
    except Exception as e:
        logger.error(f"Error simulating wrong password: {str(e)}")
        return False

# Function to monitor Windows login attempts


def monitor_windows_logins():
    global monitoring_active, alerts_history

    if not wmi_available:
        logger.error("WMI is not available. Monitoring cannot start.")
        monitoring_active = False
        return

    try:
        # Initialize COM for this thread
        import pythoncom
        pythoncom.CoInitialize()

        logger.info("Starting Windows login monitoring")
        c = wmi.WMI()

        try:
            watcher = c.Win32_NTLogEvent.watch_for(
                "creation", EventCode=4625)  # 4625 = Failed login event
            logger.info("Successfully created watcher for Event ID 4625")
        except Exception as watcher_error:
            logger.error(f"Failed to create watcher: {str(watcher_error)}")
            monitoring_active = False
            return

        while monitoring_active:
            try:
                # Check for events with timeout
                event = None
                for _ in range(10):
                    if not monitoring_active:
                        break
                    try:
                        event = watcher()
                        if event:
                            break
                    except wmi.x_wmi_timed_out:
                        pass
                    time.sleep(0.1)

                if not monitoring_active:
                    break

                if event:
                    logger.info(
                        f"Intruder detected! Event ID: {event.EventCode}")
                    image_path = capture_photo()

                    if image_path:
                        email_sent = send_alert_email(
                            image_path) if config.ENABLE_EMAIL_ALERTS else False
                        sms_sid = send_sms_alert() if config.ENABLE_SMS_ALERTS else None

                        alert_record = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "image_path": image_path,
                            "email_sent": email_sent,
                            "sms_sid": sms_sid,
                            "message": "Failed login detected! Windows security event triggered."
                        }
                        alerts_history.insert(0, alert_record)
                        logger.info("Alert recorded in history")
                        time.sleep(5)  # Prevent rapid-fire alerts

                if not monitoring_active:
                    break

                time.sleep(0.5)  # Prevent high CPU usage

            except Exception as loop_error:
                logger.error(f"Error in monitoring loop: {str(loop_error)}")
                if not monitoring_active:
                    break
                time.sleep(1)

    except Exception as e:
        logger.error(f"Error in monitoring thread: {str(e)}")
    finally:
        pythoncom.CoUninitialize()
        monitoring_active = False
        logger.info("Windows login monitoring stopped")

# Function to capture frames for streaming


def capture_frames_for_streaming():
    global camera, latest_frame, stream_active

    try:
        if camera is None:
            camera = cv2.VideoCapture(0)

        while stream_active:
            ret, frame = camera.read()
            if ret:
                latest_frame = frame
            time.sleep(0.033)  # ~30 fps

    except Exception as e:
        logger.error(f"Error in streaming thread: {str(e)}")
    finally:
        if camera is not None:
            camera.release()
            camera = None
            latest_frame = None

# Function for continuous video stream


def generate_frames():
    while True:
        try:
            if stream_active and latest_frame is not None:
                frame = latest_frame.copy()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, timestamp, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 153), 2)

                status_text = "MONITORING ACTIVE" if monitoring_active else "MONITORING INACTIVE"
                status_color = (
                    0, 255, 153) if monitoring_active else (255, 59, 48)
                cv2.putText(frame, status_text, (10, frame.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
            else:
                placeholder = create_placeholder_image(
                    "Camera inactive - Click 'Turn On Camera'")
                _, buffer = cv2.imencode('.jpg', placeholder)
                frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in generate_frames: {str(e)}")
            time.sleep(0.5)

# Create a placeholder image when camera is not active


def create_placeholder_image(message="No Camera Feed"):
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.putText(img, message, (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    return img

# Routes


@app.route('/')
def index():
    logger.info("Rendering index page")
    try:
        return render_template('index.html',
                               monitoring=monitoring_active,
                               alerts=alerts_history,
                               EMAIL_RECEIVER=config.EMAIL_RECEIVER,
                               OWNER_PHONE=config.OWNER_PHONE)
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return str(e), 500


@app.route('/video_feed')
def video_feed():
    logger.info("Video feed requested")
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    global monitoring_active, monitoring_thread

    if not monitoring_active:
        monitoring_active = True
        monitoring_thread = threading.Thread(target=monitor_windows_logins)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        return jsonify({"status": "success", "message": "Monitoring started"})
    return jsonify({"status": "info", "message": "Monitoring already active"})


@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    global monitoring_active
    if monitoring_active:
        monitoring_active = False
        return jsonify({"status": "success", "message": "Monitoring stopped"})
    return jsonify({"status": "info", "message": "Monitoring already inactive"})


@app.route('/get_alerts')
def get_alerts():
    logger.debug(f"Alerts requested, returning {len(alerts_history)} items")
    return jsonify(alerts_history)


@app.route('/test_capture', methods=['POST'])
def test_capture():
    # Capture a test image
    logger.info("Test capture requested")
    image_path = capture_photo()

    if image_path:
        # Add to history as a test
        timestamp = datetime.now()
        alert_record = {
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "image_path": image_path,
            "email_sent": False,
            "sms_sid": None,
            "message": "Test capture",
            "is_test": True
        }
        alerts_history.insert(0, alert_record)
        logger.info(f"Test capture successful: {image_path}")
        return jsonify({"status": "success", "image_path": image_path})
    else:
        logger.error("Test capture failed")
        return jsonify({"status": "error", "message": "Failed to capture image"})


@app.route('/toggle_stream', methods=['POST'])
def toggle_stream():
    global stream_active, stream_thread, camera

    enable = request.get_json().get('enable', False)
    if enable and not stream_active:
        stream_active = True
        stream_thread = threading.Thread(target=capture_frames_for_streaming)
        stream_thread.daemon = True
        stream_thread.start()
        return jsonify({"status": "success", "message": "Stream started"})
    elif not enable and stream_active:
        stream_active = False
        time.sleep(0.5)
        if camera is not None:
            camera.release()
            camera = None
        return jsonify({"status": "success", "message": "Stream stopped"})
    return jsonify({"status": "info", "message": f"Stream already {'active' if stream_active else 'inactive'}"})


@app.route('/wrong_password', methods=['POST'])
def wrong_password_trigger():
    logger.info("Wrong password trigger requested")
    if simulate_wrong_password():
        return jsonify({"status": "success", "message": "Wrong password alert triggered"})
    else:
        return jsonify({"status": "error", "message": "Failed to trigger wrong password alert"})


@app.route('/system_status')
def system_status():
    logger.debug("System status requested")
    return jsonify({
        "monitoring_active": monitoring_active,
        "stream_active": stream_active,
        "wmi_available": wmi_available,
        "email_alerts_enabled": config.ENABLE_EMAIL_ALERTS,
        "sms_alerts_enabled": config.ENABLE_SMS_ALERTS and twilio_available,
        "email_configured": bool(config.EMAIL_SENDER and config.EMAIL_PASSWORD and config.EMAIL_RECEIVER),
        "sms_configured": bool(config.TWILIO_SID and config.TWILIO_AUTH_TOKEN and config.TWILIO_PHONE and config.OWNER_PHONE),
        "alert_count": len(alerts_history)
    })

# Cleanup function to ensure resources are released


def cleanup():
    global camera, stream_active, monitoring_active
    logger.info("Performing cleanup")
    stream_active = False
    monitoring_active = False
    if camera is not None:
        logger.info("Releasing camera during cleanup")
        camera.release()
        camera = None


if __name__ == "__main__":
    try:
        logger.info("Starting IntruderVision application")
        # Ensure the static/images directory exists
        os.makedirs("static/images", exist_ok=True)

        # Ensure camera is off initially
        stream_active = False
        camera = None
        latest_frame = None

        # Register cleanup function to run at exit
        import atexit
        atexit.register(cleanup)

        print("Starting IntruderVision web server. Press CTRL+C to exit.")
        print(
            f"Access the web interface at http://{config.FLASK_HOST}:{config.FLASK_PORT}")
        print(
            f"WMI Monitoring: {'Enabled' if config.ENABLE_WMI_MONITORING and wmi_available else 'Disabled'}")
        print(
            f"Email Alerts: {'Enabled' if config.ENABLE_EMAIL_ALERTS else 'Disabled'}")
        print(
            f"SMS Alerts: {'Enabled' if config.ENABLE_SMS_ALERTS and twilio_available else 'Disabled'}")
        print("\nIMPORTANT: For real wrong password detection, run as administrator.")

        # Run without the reloader and with threading enabled
        app.run(host=config.FLASK_HOST,
                port=config.FLASK_PORT,
                debug=config.FLASK_DEBUG,
                use_reloader=False,
                threaded=True)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        cleanup()
    except Exception as e:
        logger.error(f"Application failed to start: {str(e)}")
        print(f"Error: {str(e)}")
        cleanup()
