# 🚨 Intruder Detection System  

An AI-powered security system that detects unauthorized access attempts on your Windows system. If a wrong password is entered, it captures the intruder’s photo 📷 and sends alerts via email ✉️ and SMS 📲 in real-time.  

---

## ✨ Features  
- 🔍 **Monitors Failed Login Attempts** (Event ID 4625)  
- 📷 **Captures Intruder’s Image** using the webcam  
- 📩 **Sends Email Alerts** with the intruder's photo  
- 📲 **Sends SMS Notifications** via Twilio  
- ⚡ **Fast Response** – triggers immediately upon detection  

---

## 📋 Pre-requisites  
Before running this project, ensure you have the following installed:  
- Python 3.x  
- A webcam (for capturing images)  
- Twilio account for sending SMS alerts  
- Gmail account for email notifications  

---

## 📂 Code Structure  

📂 Intruder-Detection-System 
- 📜 intruder_system.py # Main script to monitor login attempts 
- 📜 README.md # Documentation 
- 📜 requirements.txt # Required dependencies 
- 📂 assets # Stores captured images

yaml
Copy
Edit

---

## 📦 Dependencies  
Install the required Python packages:  
```bash
pip install opencv-python smtplib wmi twilio
```
Or install from requirements.txt:

```bash
pip install -r requirements.txt
```
🚀 Installation
1️⃣ Clone the repository:

```bash
git clone https://github.com/yourusername/intruder-detection.git
```
cd intruder-detection
2️⃣ Install dependencies:

```bash
pip install -r requirements.txt
```
3️⃣ Configure your credentials in the script (EMAIL_SENDER, TWILIO_SID, etc.).

🏃 Usage
Run the script to start monitoring failed login attempts:

```bash
python intruder_system.py
```
## 🔮 Future Improvements  
- ✅ Implement facial recognition to differentiate between the owner and an intruder.  
- 🚀 Optimize image capturing for better quality and speed.  
- 🔄 Store intruder logs for future analysis.  
- 🌐 Web-based dashboard for remote monitoring.  

---

## 🤝 Contributing  
Want to contribute? Follow these steps:  

1️⃣ **Fork the repository** 🍴  
2️⃣ **Create a new branch** (`feature-branch`) 🌿  
```bash
 git checkout -b feature-branch
```
3️⃣ Make your changes and commit them ✅

```bash
git commit -m "Added new feature"
```
4️⃣ Push to the branch 🚀

```bash
git push origin feature-branch
```
5️⃣ Open a pull request 🔃

Let me know if you need any modifications! 🚀

## ⚠️ Disclaimer  

This project is intended **for educational and security purposes only**. 🛑 Unauthorized use, monitoring, or surveillance of individuals **without consent** may be illegal in certain jurisdictions.  

By using this software, you agree that you are responsible for ensuring compliance with all applicable laws and regulations. 🚨 The authors of this project **are not liable** for any misuse or legal consequences resulting from its deployment.  

Use it ethically and responsibly. ✅  

