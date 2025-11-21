# db.py
import re
import datetime
import mysql.connector
from config import MYSQL_CONFIG


def connect_db():
    return mysql.connector.connect(**MYSQL_CONFIG)


def normalize_word(word: str) -> str:
    """
    More aggressive normalization for matching:
    - lower + strip
    - bodies -> body (ies -> y)
    - trailing 's' removed (but not 'ss')
    """
    if not word:
        return ""
    w = word.strip().lower()
    if w.endswith("ies"):
        w = w[:-3] + "y"
    elif w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    return w


def _insert_disease_get_id(cursor, name: str):
    name_norm = normalize_word(name)
    cursor.execute("INSERT IGNORE INTO diseases (disease_name) VALUES (%s)", (name_norm,))
    cursor.execute("SELECT disease_id FROM diseases WHERE disease_name = %s", (name_norm,))
    row = cursor.fetchone()
    return row[0]


def _insert_symptom_get_id(cursor, symptom: str):
    s = normalize_word(symptom)
    cursor.execute("INSERT IGNORE INTO symptoms (symptom_name) VALUES (%s)", (s,))
    cursor.execute("SELECT symptom_id FROM symptoms WHERE symptom_name = %s", (s,))
    row = cursor.fetchone()
    return row[0]


def _link_disease_symptom(cursor, disease_id: int, symptom_id: int):
    cursor.execute(
        "INSERT IGNORE INTO disease_symptoms (disease_id, symptom_id) VALUES (%s, %s)",
        (disease_id, symptom_id)
    )


def _add_prevention(cursor, disease_id: int, text: str):
    cursor.execute(
        "INSERT INTO preventions (disease_id, prevention_text) VALUES (%s, %s)",
        (disease_id, text)
    )


def _add_case(cursor, disease_id: int, case_date, num_cases: int):
    cursor.execute(
        "INSERT INTO cases (disease_id, case_date, num_cases) VALUES (%s, %s, %s)",
        (disease_id, case_date, num_cases)
    )


def _generate_variants(symptom: str, custom_variants: dict):
    """
    Return a set of plausible variants for a symptom:
    - include normalized original
    - include only curated custom variants (no naive pluralization)
    """
    base = normalize_word(symptom)
    variants = {base}
    if base in custom_variants:
        for v in custom_variants[base]:
            variants.add(normalize_word(v))
    return variants


def seed_database():
    """Drop tables (safely), recreate, and seed the dataset."""
    conn = connect_db()
    cursor = conn.cursor()

    db_name = MYSQL_CONFIG.get("database") if "database" in MYSQL_CONFIG else "health_db"
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    cursor.execute(f"USE `{db_name}`")


    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    cursor.execute("DROP TABLE IF EXISTS cases")
    cursor.execute("DROP TABLE IF EXISTS disease_symptoms")
    cursor.execute("DROP TABLE IF EXISTS preventions")
    cursor.execute("DROP TABLE IF EXISTS symptoms")
    cursor.execute("DROP TABLE IF EXISTS diseases")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")


    cursor.execute("""
        CREATE TABLE diseases (
            disease_id INT AUTO_INCREMENT PRIMARY KEY,
            disease_name VARCHAR(100) UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE symptoms (
            symptom_id INT AUTO_INCREMENT PRIMARY KEY,
            symptom_name VARCHAR(100) UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE disease_symptoms (
            disease_id INT,
            symptom_id INT,
            FOREIGN KEY (disease_id) REFERENCES diseases(disease_id) ON DELETE CASCADE,
            FOREIGN KEY (symptom_id) REFERENCES symptoms(symptom_id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE preventions (
            prevention_id INT AUTO_INCREMENT PRIMARY KEY,
            disease_id INT,
            prevention_text VARCHAR(255),
            FOREIGN KEY (disease_id) REFERENCES diseases(disease_id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE cases (
            case_id INT AUTO_INCREMENT PRIMARY KEY,
            disease_id INT,
            case_date DATE,
            num_cases INT,
            FOREIGN KEY (disease_id) REFERENCES diseases(disease_id) ON DELETE CASCADE
        )
    """)


    diseases_data = {
        "fever": {
            "symptoms": ["high temperature", "sweating", "chills"],
            "preventions": ["Stay hydrated", "Rest well", "Take paracetamol if needed"],
            "cases": 120
        },
        "covid": {
            "symptoms": ["cough", "fever", "loss of taste or smell"],
            "preventions": ["Wear mask", "Sanitize hands", "Get vaccinated"],
            "cases": 85
        },
        "malaria": {
            "symptoms": ["fever", "chills", "sweating"],
            "preventions": ["Use mosquito nets", "Avoid stagnant water", "Take preventive medication"],
            "cases": 64
        },
        "dengue": {
            "symptoms": ["rash", "fever", "joint pain"],
            "preventions": ["Avoid mosquito bites", "Wear full sleeves", "Use repellents"],
            "cases": 42
        },
        "typhoid": {
            "symptoms": ["abdominal pain", "fever", "headache"],
            "preventions": ["Drink clean water", "Wash fruits/vegetables", "Vaccination"],
            "cases": 32
        },
        "tuberculosis": {
            "symptoms": ["chronic cough", "weight loss", "fever"],
            "preventions": ["Vaccination (BCG)", "Good ventilation", "Avoid contact with TB patients"],
            "cases": 28
        },
        "asthma": {
            "symptoms": ["shortness of breath", "wheezing", "coughing"],
            "preventions": ["Avoid allergens", "Take inhalers", "Exercise regularly"],
            "cases": 50
        },
        "pneumonia": {
            "symptoms": ["chest pain", "fever", "cough with phlegm"],
            "preventions": ["Vaccination", "Avoid smoking", "Seek early treatment"],
            "cases": 23
        },
        "cholera": {
            "symptoms": ["diarrhea", "vomiting", "dehydration"],
            "preventions": ["Drink safe water", "Proper sanitation", "Oral rehydration"],
            "cases": 14
        },
        "hepatitis": {
            "symptoms": ["jaundice", "fatigue", "loss of appetite"],
            "preventions": ["Vaccination", "Drink clean water", "Wash hands"],
            "cases": 19
        },
        "chickenpox": {
            "symptoms": ["rash", "fever", "itching"],
            "preventions": ["Vaccination", "Avoid contact with infected", "Keep skin clean"],
            "cases": 16
        },
        "measles": {
            "symptoms": ["rash", "fever", "red eye"],
            "preventions": ["MMR vaccine", "Avoid contact with infected", "Maintain hygiene"],
            "cases": 10
        },
        "polio": {
            "symptoms": ["muscle weakness", "paralysis", "fever"],
            "preventions": ["Polio vaccine", "Good hygiene"],
            "cases": 3
        },
        "influenza": {
            "symptoms": ["fever", "body ache", "cough"],
            "preventions": ["Flu shot", "Maintain hygiene", "Rest"],
            "cases": 90
        },
        "hypertension": {
            "symptoms": ["headache", "dizziness", "chest pain"],
            "preventions": ["Eat healthy", "Exercise regularly", "Reduce salt intake"],
            "cases": 110
        }
    }

    disease_aliases = {
        "tuberculosis": ["tb"],
        "influenza": ["flu"],
        "hypertension": ["high blood pressure"]
    }

    symptom_variants = {
        "red eye": ["red eyes"],
        "chronic cough": ["cough"],
        "body ache": ["body aches"],
        "coughing": ["cough"]
    }
    symptom_variants = { normalize_word(k): [normalize_word(v) for v in vals] for k, vals in symptom_variants.items() }

    today = datetime.date.today()

    for disease, details in diseases_data.items():
        disease_id = _insert_disease_get_id(cursor, disease)

        for symptom in details["symptoms"]:
            variants = _generate_variants(symptom, symptom_variants)
            for v in variants:
                symptom_id = _insert_symptom_get_id(cursor, v)
                _link_disease_symptom(cursor, disease_id, symptom_id)

        for prevention in details["preventions"]:
            _add_prevention(cursor, disease_id, prevention.strip())

        _add_case(cursor, disease_id, today, details["cases"])

        for alias in disease_aliases.get(disease, []):
            alias_id = _insert_disease_get_id(cursor, alias)
            cursor.execute(
                "INSERT IGNORE INTO disease_symptoms (disease_id, symptom_id) "
                "SELECT %s, symptom_id FROM disease_symptoms WHERE disease_id = %s",
                (alias_id, disease_id)
            )
            cursor.execute(
                "INSERT IGNORE INTO preventions (disease_id, prevention_text) "
                "SELECT %s, prevention_text FROM preventions WHERE disease_id = %s",
                (alias_id, disease_id)
            )
            cursor.execute(
                "INSERT IGNORE INTO cases (disease_id, case_date, num_cases) "
                "SELECT %s, case_date, num_cases FROM cases WHERE disease_id = %s",
                (alias_id, disease_id)
            )

        conn.commit()

    cursor.close()
    conn.close()
    print("✅ Database seeded successfully with clean symptom variants!")



def _dedup_symptoms(raw: str):
    """Collapse variants into canonical unique symptoms (comma-separated)."""
    if not raw:
        return ""
    raw_syms = [s.strip() for s in raw.split(",")]
    canonical = {normalize_word(s) for s in raw_syms}
    return ", ".join(sorted(canonical))


def get_disease_info(disease_name):
    conn = connect_db()
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

    if result and result.get("symptoms"):
        result["symptoms"] = _dedup_symptoms(result["symptoms"])

    cursor.close()
    conn.close()
    return result


def get_disease_by_symptom(symptom):
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    norm_symptom = normalize_word(symptom)
    query = """
    SELECT DISTINCT d.disease_name AS disease
    FROM diseases d
    JOIN disease_symptoms ds ON d.disease_id = ds.disease_id
    JOIN symptoms s ON ds.symptom_id = s.symptom_id
    WHERE LOWER(s.symptom_name) LIKE %s
    """
    cursor.execute(query, ("%" + norm_symptom + "%",))
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results


def get_today_alert(disease_name, today):
    """
    Returns a list of alerts (disease, cases, date) for diseases matching `disease_name` (LIKE),
    on given date. This always returns a list (possibly empty).
    """
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT d.disease_name AS disease, c.num_cases AS cases, c.case_date AS date
    FROM cases c
    JOIN diseases d ON c.disease_id = d.disease_id
    WHERE LOWER(d.disease_name) LIKE %s AND c.case_date = %s
    """
    cursor.execute(query, ("%" + disease_name.lower() + "%", today))
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results


def get_diseases_by_multiple_symptoms(symptoms):
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    normalized = [normalize_word(s) for s in symptoms if s.strip()]
    if not normalized:
        return []

    like_clauses = " OR ".join(["LOWER(s.symptom_name) LIKE %s" for _ in normalized])
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

    values = [f"%{sym}%" for sym in normalized]
    cursor.execute(query, values)
    results = cursor.fetchall()

    for row in results:
        if row.get("symptoms"):
            row["symptoms"] = _dedup_symptoms(row["symptoms"])

    cursor.close()
    conn.close()
    return results


def get_all_diseases():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT disease_name AS disease FROM diseases"
    cursor.execute(query)
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results


if __name__ == "__main__":
    seed_database()
