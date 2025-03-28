# Bot Whatsapp de Atencion al cliente de Imagenes

---

## **📂 Project Structure**
```bash
python-whatsapp-bot/
│── .env                     # Environment variables (update with your WhatsApp API keys)
│── run.py                    # Main Flask app runner
│── requirements.txt          # Dependencies list
│── README.md                 # This documentation
│
├── app/                      # Main application logic
│   ├── __init__.py           # Initializes Flask app
│   ├── views.py              # Handles incoming WhatsApp messages (webhooks)
│   ├── config.py             # Loads configurations from .env
│   │
│   ├── services/             # Service logic for processing requests
│   │   ├── whatsapp_utils.py  # WhatsApp API functions (message processing)
│   │
│   ├── utils/                # Utility functions for file and API management
│   │   ├── file_utils.py      # Handles CSV and session file management
│   │
│   └── decorators/           # Security-related decorators
│       ├── security.py        # Verifies webhook requests

---

## **🚀 How to Set Up and Run**
### **1️⃣ Install Dependencies**
Ensure you have Python installed, then install dependencies:
```bash
pip install -r requirements.txt
```

---

### **2️⃣ Set Up Environment Variables**
Create a **`.env`** file in the root directory and update it with your WhatsApp API credentials:

```ini
ACCESS_TOKEN=your_facebook_whatsapp_api_access_token
PHONE_NUMBER_ID=your_whatsapp_phone_number_id
VERSION=v22.0  # Update this if needed
VERIFY_TOKEN=your_custom_verification_token
```
Replace `your_facebook_whatsapp_api_access_token` with your **WhatsApp API token**.

---

### **3️⃣ Run the Flask App**
Start the Flask application:
```bash
python run.py
```

---

### **4️⃣ Set Up a Public URL with Ngrok**
To receive messages from WhatsApp, you need a **public URL**. Use **Ngrok** to expose your local Flask server:

1. Open a new terminal and run:
   ```bash
   ngrok http 8000
   ```
2. Copy the **public HTTPS URL** (e.g., `https://abcd-1234.ngrok.io`).
3. Go to **Meta Developer Portal** → WhatsApp → Webhook settings.
4. Paste the **Ngrok URL** followed by `/webhook`:
   ```
   https://abcd-1234.ngrok.io/webhook
   ```
5. Set the **Verify Token** (must match the `VERIFY_TOKEN` in `.env`).

---

ks the last report as urgent**.  
✅ **Secure Webhook Validation** with **HMAC signature verification**.

---
