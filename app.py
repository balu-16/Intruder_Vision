import os
import sys
import cv2
import smtplib
import time
import logging
import threading
import random
from collections import deque
from email.message import EmailMessage
from flask import Flask, render_template, jsonify, Response, request
from datetime import datetime
import numpy as np

# --- Named Constants ---
CAMERA_INIT_DELAY = 1.0          # seconds to wait after camera init
ALERT_COOLDOWN_SECONDS = 5       # prevent rapid-fire alerts
STREAM_FRAME_INTERVAL = 0.033    # ~30 fps
FRAME_DELAY_SECONDS = 0.1        # delay between MJPEG frames
MONITOR_LOOP_DELAY = 0.5         # polling interval in monitor loop
ERROR_RECOVERY_DELAY = 1.0       # pause after monitoring loop error
GENERATE_ERROR_DELAY = 0.5       # pause after generate_frames error
PLACEHOLDER_WIDTH = 400
PLACEHOLDER_HEIGHT = 300
MAX_ALERTS_HISTORY = 100          # max alerts kept in memory
TIMESTAMP_POSITION = (10, 30)
TIMESTAMP_FONT_SCALE = 0.8
TIMESTAMP_COLOR = (0, 255, 153)
STATUS_FONT_SCALE = 0.8
STATUS_ACTIVE_COLOR = (0, 255, 153)
STATUS_INACTIVE_COLOR = (255, 59, 48)
PLACEHOLDER_TEXT_POSITION = (50, 150)
PLACEHOLDER_FONT_SCALE = 0.8
PLACEHOLDER_TEXT_COLOR = (255, 255, 255)
TEXT_THICKNESS = 2
IS_WINDOWS = sys.platform == "win32"

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
        FLASK_DEBUG = False

# Import optional dependencies
wmi_available = False
twilio_available = False

if config.ENABLE_WMI_MONITORING:
    if not IS_WINDOWS:
        logger.info("WMI monitoring skipped: not running on Windows")
        config.ENABLE_WMI_MONITORING = False
    else:
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
_state_lock = threading.Lock()
monitoring_active = False
monitoring_thread = None
alerts_history = deque(maxlen=MAX_ALERTS_HISTORY)
camera = None
stream_active = False
stream_thread = None
latest_frame = None

# Function to capture image


def capture_photo():
    global camera, latest_frame
    try:
        with _state_lock:
            # Use latest frame if available and streaming is active
            if latest_frame is not None and stream_active:
                frame_copy = latest_frame.copy()
            else:
                frame_copy = None

        if frame_copy is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_path = f"static/images/capture_{timestamp}.jpg"
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            cv2.imwrite(img_path, frame_copy)
            return img_path

        # Initialize camera if needed
        needs_init = False
        with _state_lock:
            if camera is None:
                camera = cv2.VideoCapture(0)
                needs_init = True

        if needs_init:
            time.sleep(CAMERA_INIT_DELAY)

        with _state_lock:
            local_cam = camera

        if local_cam is None:
            return None

        ret, frame = local_cam.read()
        if ret:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            img_path = f"static/images/capture_{timestamp}.jpg"
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            cv2.imwrite(img_path, frame)

            with _state_lock:
                if not stream_active and camera is not None:
                    camera.release()
                    camera = None

            return img_path
        return None
    except Exception as e:
        logger.error(f"Error capturing photo: {str(e)}")
        with _state_lock:
            if not stream_active and camera is not None:
                camera.release()
                camera = None
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
            with _state_lock:
                alerts_history.appendleft(alert_record)
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
                        with _state_lock:
                            alerts_history.appendleft(alert_record)
                        logger.info("Alert recorded in history")
                        time.sleep(ALERT_COOLDOWN_SECONDS)  # Prevent rapid-fire alerts

                if not monitoring_active:
                    break

                time.sleep(MONITOR_LOOP_DELAY)  # Prevent high CPU usage

            except Exception as loop_error:
                logger.error(f"Error in monitoring loop: {str(loop_error)}")
                if not monitoring_active:
                    break
                time.sleep(ERROR_RECOVERY_DELAY)

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
        with _state_lock:
            if camera is None:
                camera = cv2.VideoCapture(0)

        while True:
            with _state_lock:
                if not stream_active:
                    break
                local_cam = camera

            if local_cam is None:
                break
            ret, frame = local_cam.read()
            if ret:
                with _state_lock:
                    latest_frame = frame
            time.sleep(STREAM_FRAME_INTERVAL)  # ~30 fps

    except Exception as e:
        logger.error(f"Error in streaming thread: {str(e)}")
    finally:
        with _state_lock:
            if camera is not None:
                camera.release()
                camera = None
            latest_frame = None
            stream_active = False

# Function for continuous video stream


def generate_frames():
    while True:
        with _state_lock:
            if not stream_active and latest_frame is None:
                # Stream is off and no frame to serve — yield placeholder then exit
                pass
        try:
            with _state_lock:
                local_active = stream_active
                local_frame = latest_frame.copy() if latest_frame is not None else None

            if local_active and local_frame is not None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(local_frame, timestamp, TIMESTAMP_POSITION,
                            cv2.FONT_HERSHEY_SIMPLEX, TIMESTAMP_FONT_SCALE, TIMESTAMP_COLOR, TEXT_THICKNESS)

                with _state_lock:
                    mon_active = monitoring_active
                status_text = "MONITORING ACTIVE" if mon_active else "MONITORING INACTIVE"
                status_color = STATUS_ACTIVE_COLOR if mon_active else STATUS_INACTIVE_COLOR
                cv2.putText(local_frame, status_text, (10, local_frame.shape[0] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, STATUS_FONT_SCALE, status_color, TEXT_THICKNESS)

                _, buffer = cv2.imencode('.jpg', local_frame)
                frame_bytes = buffer.tobytes()
            else:
                placeholder = create_placeholder_image(
                    "Camera inactive - Click 'Turn On Camera'")
                _, buffer = cv2.imencode('.jpg', placeholder)
                frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(FRAME_DELAY_SECONDS)

        except Exception as e:
            logger.error(f"Error in generate_frames: {str(e)}")
            time.sleep(GENERATE_ERROR_DELAY)

# Create a placeholder image when camera is not active


def create_placeholder_image(message="No Camera Feed"):
    img = np.zeros((PLACEHOLDER_HEIGHT, PLACEHOLDER_WIDTH, 3), dtype=np.uint8)
    cv2.putText(img, message, PLACEHOLDER_TEXT_POSITION,
                cv2.FONT_HERSHEY_SIMPLEX, PLACEHOLDER_FONT_SCALE, PLACEHOLDER_TEXT_COLOR, TEXT_THICKNESS)
    return img

# Routes


@app.route('/')
def index():
    logger.info("Rendering index page")
    try:
        with _state_lock:
            mon_active = monitoring_active
            alerts_copy = list(alerts_history)
        return render_template('index.html',
                               monitoring=mon_active,
                               alerts=alerts_copy,
                               EMAIL_RECEIVER=config.EMAIL_RECEIVER,
                               OWNER_PHONE=config.OWNER_PHONE)
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/video_feed')
def video_feed():
    logger.info("Video feed requested")
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/start_monitoring', methods=['POST'])
def start_monitoring():
    global monitoring_active, monitoring_thread

    with _state_lock:
        current_monitoring = monitoring_active

    if not current_monitoring:
        with _state_lock:
            monitoring_active = True
        monitoring_thread = threading.Thread(target=monitor_windows_logins)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        return jsonify({"status": "success", "message": "Monitoring started"})
    return jsonify({"status": "info", "message": "Monitoring already active"})


@app.route('/stop_monitoring', methods=['POST'])
def stop_monitoring():
    global monitoring_active
    with _state_lock:
        current_monitoring = monitoring_active
    if current_monitoring:
        with _state_lock:
            monitoring_active = False
        return jsonify({"status": "success", "message": "Monitoring stopped"})
    return jsonify({"status": "info", "message": "Monitoring already inactive"})


@app.route('/get_alerts')
def get_alerts():
    with _state_lock:
        alerts_copy = list(alerts_history)
    logger.debug(f"Alerts requested, returning {len(alerts_copy)} items")
    return jsonify({"status": "success", "message": "Alerts retrieved", "alerts": alerts_copy})


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
        with _state_lock:
            alerts_history.appendleft(alert_record)
        logger.info(f"Test capture successful: {image_path}")
        return jsonify({"status": "success", "message": "Test capture successful", "image_path": image_path})
    else:
        logger.error("Test capture failed")
        return jsonify({"status": "error", "message": "Failed to capture image"})


@app.route('/toggle_stream', methods=['POST'])
def toggle_stream():
    global stream_active, stream_thread, camera

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"status": "error", "message": "Request body must be valid JSON with an 'enable' boolean field"}), 400
    enable = data.get('enable')
    if not isinstance(enable, bool):
        return jsonify({"status": "error", "message": "'enable' field must be a boolean"}), 400

    with _state_lock:
        current_active = stream_active

    if enable and not current_active:
        with _state_lock:
            stream_active = True
        stream_thread = threading.Thread(target=capture_frames_for_streaming)
        stream_thread.daemon = True
        stream_thread.start()
        return jsonify({"status": "success", "message": "Stream started"})
    elif not enable and current_active:
        with _state_lock:
            stream_active = False
        if stream_thread is not None:
            stream_thread.join(timeout=2.0)
        return jsonify({"status": "success", "message": "Stream stopped"})
    return jsonify({"status": "info", "message": f"Stream already {'active' if current_active else 'inactive'}"})


@app.route('/wrong_password', methods=['POST'])
def wrong_password_trigger():
    logger.info("Wrong password trigger requested")
    if simulate_wrong_password():
        return jsonify({"status": "success", "message": "Wrong password alert triggered"})
    else:
        return jsonify({"status": "error", "message": "Failed to trigger wrong password alert"})


@app.route('/system_status')
def system_status():
    try:
        logger.debug("System status requested")
        with _state_lock:
            mon_active = monitoring_active
            str_active = stream_active
            alert_count = len(alerts_history)
        return jsonify({
            "monitoring_active": mon_active,
            "stream_active": str_active,
            "wmi_available": wmi_available,
            "email_alerts_enabled": config.ENABLE_EMAIL_ALERTS,
            "sms_alerts_enabled": config.ENABLE_SMS_ALERTS and twilio_available,
            "email_configured": bool(config.EMAIL_SENDER and config.EMAIL_PASSWORD and config.EMAIL_RECEIVER),
            "sms_configured": bool(config.TWILIO_SID and config.TWILIO_AUTH_TOKEN and config.TWILIO_PHONE and config.OWNER_PHONE),
            "alert_count": alert_count
        })
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Cleanup function to ensure resources are released


def cleanup():
    global camera, stream_active, monitoring_active
    logger.info("Performing cleanup")
    with _state_lock:
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
