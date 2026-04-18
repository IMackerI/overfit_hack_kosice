import requests
from config import BOT_TOKEN

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    text_lower = text.lower()

    # TODO Agent stuff
    if text_lower == "hi":
        send_message(chat_id, "👋 Hello!")
    elif text_lower == "/help":
        send_message(chat_id, "Commands: hi, /help")
    else:
        send_message(chat_id, f"You said: {text}")
