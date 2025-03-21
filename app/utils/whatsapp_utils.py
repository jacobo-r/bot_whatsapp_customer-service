import logging
from flask import current_app, jsonify
import json
import requests
from app.utils.chat_utils import *

# from app.services.openai_service import generate_response
import re


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def generate_response(response):
    # Return text in uppercase
    return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text




user_states = {}  # Temporary in-memory storage of user states


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    #name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    #message_body = message["text"]["body"]
    #print(body)
    #print("nananananana")
    print(message)

    #response = generate_response(message_body)
    #data = get_text_message_input(current_app.config["RECIPIENT_WAID"], response)
    #send_message(data)
    #chat(wa_id, message)
    radiology_chat(wa_id, message)


def chat(wa_id, message):
    message_type = message["type"]

    # Check if user exists in state tracking
    if wa_id not in user_states:
        user_states[wa_id] = "waiting_for_voice"  # Initial state
        send_message(get_text_message_input(wa_id, "Please send a voice message."))
        return

    state = user_states[wa_id]

    # If waiting for voice, check if we received an audio message
    # we need to do sth if they send a text at this point , else we might be trapped. maybe a switchcase or sth
    if state == "waiting_for_voice" and message_type == "audio":
        #audio_id = message["audio"]["id"]                     ------------------------------------------------
        print(message)
        audio_url = "test.com" #get_audio_url(audio_id)  # Function to get audio URL
        user_states[wa_id] = {"state": "waiting_for_option", "audio_url": audio_url}
        send_message(get_choice_message(wa_id))  # Send multiple-choice message
        return

    # If waiting for multiple choice response
    if state.get("state") == "waiting_for_option":
        user_choice = message["text"]["body"]
        user_states[wa_id]["choice"] = user_choice
        send_message(get_yes_no_message(wa_id))  # Ask for confirmation
        user_states[wa_id]["state"] = "waiting_for_confirmation"
        return

    # If waiting for confirmation
    if state.get("state") == "waiting_for_confirmation":
        if message["text"]["body"].lower() == "yes":
            save_data(wa_id, state["audio_url"], state["choice"])  # Store info
            send_message(get_text_message_input(wa_id, "Thank you! Goodbye."))
            del user_states[wa_id]  # Remove user from memory
        else:
            send_message(get_choice_message(wa_id))  # Restart choice question
            user_states[wa_id]["state"] = "waiting_for_option"
        return

def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )




"""
 ---------------------------------------------------------------    RADIOLOGY CHAT    ---------------------------------------------------------------
 
"""

SESSIONS_FILE = "./files/sessions.json"
REPORTS_FILE = "./files/reports.csv"
save_dir= "./wapp_audios"

# Exam types in Spanish #TODO make more robust, add orthography robustness
VALID_EXAM_TYPES = {
    "resonancia": "Resonancia",
    "tomografía": "Tomografía",
    "rayos x": "Digital (Rayos X)",
    "ecografía": "Ecografía",
    "estudios especiales": "Estudios Especiales"
}


def radiology_chat(wa_id, message):
    """Handles chat flow for radiologists recording medical reports via WhatsApp voice messages."""

    sessions = load_sessions(SESSIONS_FILE)  # Load doctor sessions
    message_type = message["type"]
    current_exam_type = sessions.get(wa_id, None)
    print("INTO THE PROCESSING")
    # Process text messages
    if message_type == "text":
        handle_text_message(wa_id, message["text"]["body"].strip().lower(), sessions, current_exam_type)
        return

    # Process audio messages
    if message_type == "audio":
        handle_audio_message(wa_id, message["audio"]["id"], current_exam_type)
        return

    # If an unsupported message type is received
    send_message(get_text_message_input(
        wa_id, "Solo puedo procesar mensajes de texto y audios."
    ))

def handle_text_message(wa_id, text_message, sessions, current_exam_type):
    """Handles incoming text messages from doctors."""

    # ✅ BORRAR Logic: If "BORRAR" is sent, delete the last report
    if text_message == "borrar":
        if delete_last_medical_report(wa_id, REPORTS_FILE):
            send_message(get_text_message_input(wa_id, "El último estudio registrado ha sido eliminado."))
        else:
            send_message(get_text_message_input(wa_id, "No se encontró ningún estudio previo para eliminar."))
        return

    # ✅ URGENTE Logic: If "URGENTE" is sent, mark the last report as urgent
    if text_message == "urgente":
        if mark_report_as_urgent(wa_id, REPORTS_FILE):
            send_message(get_text_message_input(wa_id, "Marcado como *URGENTE*."))
        else:
            send_message(get_text_message_input(wa_id, "No se encontró ningún estudio previo para marcar como urgente."))
        return

    # ✅ If the text matches an exam type, update the session
    new_exam_type = detect_exam_type(text_message,VALID_EXAM_TYPES)
    if new_exam_type:
        sessions[wa_id] = new_exam_type
        save_sessions(sessions, SESSIONS_FILE)
        #print("SAVED SESSION")
        send_message(get_text_message_input(
            wa_id, 
            f"Todos los estudios ahora serán considerados como: *{new_exam_type}*"
            
        ))
        return

    # ✅ If doctor is in a session but sent an invalid text
    if current_exam_type:
        #print("INVALID TEXT")
        send_message(get_text_message_input(
            wa_id, "Intentelo de nuevo, opciones:"
            "* Resonancia\n* Tomografía\n* Digital (Rayos X)\n* Ecografía\n* Estudios especiales"

        ))
    else:
        send_message(get_text_message_input(
            wa_id, 
            "Por favor, indique el tipo de estudio antes de comenzar:\n"
            "* Resonancia\n* Tomografía\n* Digital (Rayos X)\n* Ecografía\n* Estudios especiales"
        ))


def handle_audio_message(wa_id, audio_id, current_exam_type):
    """Handles incoming audio messages from doctors."""

    # ✅ If the doctor is NOT in a session, ask them to define one first
    if not current_exam_type:
        send_message(get_text_message_input(
            wa_id, 
            "Antes de grabar estudios, por favor indique el tipo de estudio en el chat:\n"
            "* Resonancia\n* Tomografía\n* Rayos X\n* Ecografía\n* Estudios especiales\n"
            "Si mando un audio medico antes de hacer esto, por favor mandelo de nuevo!."
        ))
        return

    # ✅ Extract audio URL and store the report ######## ADD HERE the download MECHANIC
    audio_url = get_audio_url(audio_id)
    save_medical_report(wa_id, audio_url, current_exam_type, REPORTS_FILE)
    download_audio_from_whatsapp(audio_url, current_app.config['ACCESS_TOKEN'], save_dir)

    send_message(get_text_message_input(
        wa_id, 
        f"Audio enviado como *{current_exam_type}*.\n"
        "Puede BORRAR o marcar el audio como URGENTE"
    ))



def download_audio_from_whatsapp(audio_url, whatsapp_access_token, save_dir):
    headers = {
        "Authorization": f"Bearer {whatsapp_access_token}"
    }

    response = requests.get(audio_url, headers=headers)
    
    if response.status_code == 200:
        content_type = response.headers.get("content-type", "")
        extension = get_extension_from_mime(content_type)
        
        if not extension:
            print(f"❌ Unknown MIME type: {content_type}")
            return None
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audio_{timestamp}.{extension}"
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.content)

        print(f"✅ Audio saved to {filepath}")
        return filepath
    else:
        print(f"❌ Failed to download audio: {response.status_code} {response.text}")
        return None

def get_extension_from_mime(mime_type):
    mapping = {
        "audio/ogg": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp4": "mp4",
        "video/mp4": "mp4",
        "audio/aac": "aac",
        "audio/webm": "webm"
    }
    return mapping.get(mime_type, None)