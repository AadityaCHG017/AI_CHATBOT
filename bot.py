from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import random
import datetime
from deep_translator import GoogleTranslator
import mysql.connector


ACCOUNT_SID = ""
AUTH_TOKEN = ""
TWILIO_WHATSAPP = ""  
USER_WHATSAPP = ""   

# MySQL credentials
db_config = {
    "host": "",
    "user": "",
    "password": "",
    "database": ""
}


user_sessions = {}

# Init Twilio client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Init Flask app
app = Flask(__name__)


def get_random_disease():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.disease_name, c.num_cases
        FROM cases c
        JOIN diseases d ON c.disease_id = d.disease_id
        WHERE c.case_date = CURDATE()
    """)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    if results:
        return random.choice(results)
    return None

def get_disease_info(disease_name):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    query = """
    SELECT d.disease_name AS disease,
           GROUP_CONCAT(DISTINCT s.symptom_name) AS symptoms,
           GROUP_CONCAT(DISTINCT p.prevention_text) AS prevention
    FROM diseases d
    LEFT JOIN disease_symptoms ds ON d.disease_id = ds.disease_id
    LEFT JOIN symptoms s ON ds.symptom_id = s.symptom_id
    LEFT JOIN preventions p ON d.disease_id = p.disease_id
    WHERE LOWER(d.disease_name) LIKE %s
    GROUP BY d.disease_id
    """
    cursor.execute(query, ("%" + disease_name.lower() + "%",))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def get_diseases_by_multiple_symptoms(symptoms):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    like_clauses = " OR ".join(["LOWER(s.symptom_name) LIKE %s" for _ in symptoms])
    query = f"""
    SELECT d.disease_name AS disease,
           GROUP_CONCAT(DISTINCT s.symptom_name) AS symptoms,
           GROUP_CONCAT(DISTINCT p.prevention_text) AS prevention,
           COUNT(DISTINCT s.symptom_id) AS matched_symptoms
    FROM diseases d
    JOIN disease_symptoms ds ON d.disease_id = ds.disease_id
    JOIN symptoms s ON ds.symptom_id = s.symptom_id
    LEFT JOIN preventions p ON d.disease_id = p.disease_id
    WHERE {like_clauses}
    GROUP BY d.disease_id
    HAVING matched_symptoms >= 1
    ORDER BY matched_symptoms DESC
    """
    values = [f"%{s.strip().lower()}%" for s in symptoms if s.strip()]
    cursor.execute(query, values)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def send_startup_alert():
    disease = get_random_disease()
    if disease:
        disease_name, num_cases = disease
        alert_msg = f"Disease Alert: Today {disease_name} has {num_cases} reported cases.\n\nChoose your language: Hindi, Odia, English"
    else:
        alert_msg = "No disease data found for today."

    client.messages.create(
        from_=TWILIO_WHATSAPP,
        to=USER_WHATSAPP,
        body=alert_msg
    )
    print("Startup alert sent!")


def get_vaccine_schedule(language="en"):
    schedule = """
💉 *Complete Vaccine Schedule (India)*

👶 **At Birth**
- BCG (Tuberculosis)
- Hepatitis B (1st dose)
- OPV 0 (Oral Polio Vaccine)

🗓️ **6 Weeks**
- DTP (1st dose)
- IPV (Polio - 1st dose)
- Hepatitis B (2nd dose)
- Hib (1st dose)
- Rotavirus (1st dose)
- PCV (Pneumococcal - 1st dose)

🗓️ **10 Weeks**
- DTP (2nd dose)
- IPV (2nd dose)
- Hib (2nd dose)
- Rotavirus (2nd dose)
- PCV (2nd dose)

🗓️ **14 Weeks**
- DTP (3rd dose)
- IPV (3rd dose)
- Hib (3rd dose)
- Rotavirus (3rd dose)
- PCV (3rd dose)

🎂 **9–12 Months**
- Measles / MMR
- JE vaccine (in endemic areas)
- Hepatitis A (1st dose)
- PCV booster

🧒 **15–18 Months**
- DTP booster
- Hib booster
- MMR (2nd dose)
- Varicella

👧 **4–6 Years**
- DTP booster
- Polio booster
- MMR (3rd dose)
- Varicella (2nd dose)

🧑 **10–12 Years**
- Tdap
- HPV (for girls)
- Typhoid booster
    """

    # Translate if language is not English
    if language != "en":
        try:
            schedule = GoogleTranslator(source='en', target=language).translate(schedule)
        except Exception as e:
            print("Translation failed:", e)

    return schedule

@app.route("/webhook", methods=["GET","POST"])
def webhook():
    
    resp = MessagingResponse()
    try:
        incoming_msg = request.values.get("Body", "").strip().lower()
        from_number = request.values.get("From", "")
        print("Incoming message:", incoming_msg, "From:", from_number)

        reply = ""

        if from_number not in user_sessions:
            user_sessions[from_number] = {"language": None}
        session = user_sessions[from_number]

        # STEP 1: Language selection
        if not session["language"]:
            if "english" in incoming_msg:
                session["language"] = "en"
                reply = "You selected English. "
            elif "hindi" in incoming_msg or "हिंदी" in incoming_msg:
                session["language"] = "hi"
                reply = "आपने हिंदी चुना है। "
            elif "odia" in incoming_msg or "ଓଡ଼ିଆ" in incoming_msg:
                session["language"] = "or"
                reply = "ଆପଣ ଓଡ଼ିଆ ବାଛିଛନ୍ତି "
            else:
                reply = "Please reply with Hindi(हिन्दी), Odia(ହିନ୍ଦୀ), or English."
            resp.message(reply)
            return str(resp)

        # STEP 2: Process queries
        lang = session["language"]
        user_query = incoming_msg

        if lang != "en":
            user_query = GoogleTranslator(source="auto", target="en").translate(user_query)

        # Vaccine Schedule
        if "vaccine" in user_query.lower() and "schedule" in user_query.lower():
            msg = get_vaccine_schedule(lang)
            resp.message(msg)
            return str(resp)

        if "," in user_query:
            symptoms = [s.strip() for s in user_query.split(",")]
            diseases = get_diseases_by_multiple_symptoms(symptoms)
            if diseases:
                msg = "Possible diseases:\n"
                for d in diseases:
                    msg += f"- {d['disease']}: Symptoms [{d['symptoms']}], Prevention [{d['prevention']}]\n"
            else:
                msg = "No diseases found matching those symptoms."
        else:
            info = get_disease_info(user_query)
            if info:
                msg = f"ℹ{info['disease']}\nSymptoms: {info['symptoms']}\nPrevention: {info['prevention']}"
            else:
                diseases = get_diseases_by_multiple_symptoms([user_query])
                if diseases:
                    msg = "Possible diseases:\n"
                    for d in diseases:
                        msg += f"- {d['disease']}: Symptoms [{d['symptoms']}], Prevention [{d['prevention']}]\n"
                else:
                    msg = f"No data found for '{incoming_msg}'."

        if lang != "en":
            target = "hi" if lang == "hi" else "or"
            msg = GoogleTranslator(source="en", target=target).translate(msg)

        resp.message(msg)
        return str(resp)

    except Exception as e:
        print("Error reading request:", e)
        return "Error", 500


@app.route("/", methods=["GET"])
def home():
    return "Server is running!"

if __name__ == "__main__":
    #send_startup_alert()  # send alert immediately when bot starts
    app.run(port=5000, debug=True)