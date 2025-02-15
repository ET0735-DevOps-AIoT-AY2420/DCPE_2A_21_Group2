import requests
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Replace with your actual bot token and chat ID
BOT_TOKEN = "7722732406:AAFEAXz_RTJNRAnE9aRnOVtlN18G7V-0wWU"
CHAT_ID = "1498916836"

# Message to send
MESSAGE = "Hello! This is a test message from your Telegram bot."

# Telegram API URL
URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Payload (message data)
payload = {
    "chat_id": CHAT_ID,
    "text": MESSAGE
}

# Send the request
response = requests.post(URL, json=payload)

# Print the response (optional)
if response.status_code == 200:
    print("✅ Message sent successfully!")
else:
    print(f"❌ Failed to send message. Error: {response.text}")
