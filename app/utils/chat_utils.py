
import logging
from flask import current_app, jsonify
import json
import requests
import os
import csv
from datetime import datetime


def get_audio_url(audio_id):
    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{audio_id}"
    headers = {"Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()["url"]
    else:
        logging.error("Failed to get audio URL")
        return None

def get_choice_message(recipient):
    return json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"body": "Choose an option:\n1️⃣ Option 1\n2️⃣ Option 2\n3️⃣ Option 3"}
    })

def get_yes_no_message(recipient):
    return json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"body": "Are you sure?\n✅ Yes\n❌ No"}
    })

def save_data(phone_number, audio_url, choice):
    with open("user_choices.csv", "a") as f:
        f.write(f"{phone_number},{audio_url},{choice}\n")

# RADIOLOGY CHAT ---------------------------

def load_sessions(SESSIONS_FILE):
    """Load doctor sessions from a JSON file."""
    if not os.path.exists(SESSIONS_FILE):
        return {}

    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_sessions(sessions, SESSIONS_FILE):
    """Save doctor sessions to a JSON file."""
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=4)


def detect_exam_type(text, VALID_EXAM_TYPES):
    """Check if the received text matches an exam type."""
    text_lower = text.lower()
    for keyword, exam_type in VALID_EXAM_TYPES.items():
        if keyword in text_lower:
            return exam_type
    return None



def save_medical_report(phone_number, audio_url, exam_type, file_path):
    """Save the recorded audio along with the exam type in a CSV file."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_path, "a", encoding="utf-8", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow([phone_number, audio_url, exam_type, "False", current_time])  # "False" for urgente column




def delete_last_medical_report(phone_number, file_path):
    """Deletes the most recent medical report for a specific doctor while preserving other records."""
    
    if not os.path.exists(file_path):
        return False

    records = []
    deleted = False

    # Read all records into memory
    with open(file_path, "r", encoding="utf-8") as f:
        csv_reader = list(csv.reader(f))  # Convert to a list to allow reverse iteration
    
    # Iterate **backwards** to find the latest entry for the doctor
    for i in range(len(csv_reader) - 1, -1, -1):
        if csv_reader[i] and csv_reader[i][0] == phone_number:
            del csv_reader[i]  # Remove the last occurrence of this doctor's record
            deleted = True
            break  # Stop after deleting the most recent entry

    # If nothing was deleted, return False
    if not deleted:
        return False

    # Rewrite the file with remaining records
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(csv_reader)  # Write back the updated list

    return True  # Successfully deleted the last entry


def mark_report_as_urgent(phone_number, file_path):
    """Marks the last recorded medical report as urgent by updating the CSV."""
    
    if not os.path.exists(file_path):
        return False

    records = []
    updated = False

    # Read all records into memory
    with open(file_path, "r", encoding="utf-8") as f:
        csv_reader = list(csv.reader(f))  # Convert to a list to allow modifications
    
    # Iterate **backwards** to find the latest entry for the doctor
    for i in range(len(csv_reader) - 1, -1, -1):
        if csv_reader[i] and csv_reader[i][0] == phone_number:
            csv_reader[i][3] = "True"  # Mark the "URGENTE" column as True
            updated = True
            break  # Stop after updating the latest record

    # If no record was updated, return False
    if not updated:
        return False

    # Rewrite the file with updated records
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(csv_reader)  # Write back the updated list

    return True  # Successfully updated the last entry