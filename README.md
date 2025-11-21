# Flask SMS & WhatsApp Automation Project

This is a Flask-based automation project that uses **Twilio API** to send SMS and WhatsApp messages, along with a **MySQL database** for storing and managing health-related data.



## Features
- Send SMS using Twilio  
- Send WhatsApp messages  
- Store and fetch data from MySQL  
- Flask backend with clean routes  
- Secure configuration using `.env` file  



## 📂 Project Structure

project/
│── app.py
│── config.py
│── wap.py
│── requirements.txt
│── .venv
│── README.md
└── templates/



## 🔧 Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/USERNAME/REPO-NAME.git
cd REPO-NAME

2. Create virtual environment

python3 -m venv venv
source venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Setup environment variables

Create a .env file:

TWILIO_ACCOUNT_SID=xxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxx
TWILIO_PHONE_NUMBER=+12345678
MY_WHATSAPP_NUMBER=whatsapp:+91xxxxxxxx
MYSQL_HOST=127.0.0.1
MYSQL_USER=root
MYSQL_PASSWORD=xxxxxxx
MYSQL_DATABASE=health_db


⸻

▶ Run The Server

python app.py

Server will start at:

http://127.0.0.1:5000


⸻

🛠 Technologies Used
	•	Python / Flask
	•	Twilio REST API
	•	MySQL
	•	dotenv

⸻

🤝 Contributing

Feel free to create issues or submit pull requests.


If you want, I can:

-Add screenshots / API routes section  
-Write a more advanced README

Just tell me!
