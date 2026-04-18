import requests
from config import BOT_TOKEN
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
from baml_client.types import Message, Debt

BOT_USERNAME = "hack_kosice_bot"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# class Debt(BaseModel):
#     debtor: str
#     creditor: str
#     amount: float

# class Message(BaseModel):
#     user_name: str
#     text: str

client = MongoClient("mongodb://localhost:27017/")
db = client["telegram_bot"]
messages_col = db["messages"]

def save_message(message):
    doc = {
        "chat_id": message["chat"]["id"],
        "user_id": message["from"]["id"],
        "username": message["from"].get("username"),
        "timestamp": datetime.now(timezone.utc),
    }

    # text message
    if "text" in message:
        doc["type"] = "text"
        doc["text"] = message["text"]

    # photo message
    elif "photo" in message:
        doc["type"] = "photo"

        # Telegram sends multiple sizes → last one is highest quality
        photo = message["photo"][-1]

        doc["file_id"] = photo["file_id"]
        doc["caption"] = message.get("caption", "")

    messages_col.insert_one(doc)

def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


def get_last_hour_messages(chat_id):
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    cursor = messages_col.find({
        "chat_id": chat_id,
        "timestamp": {"$gte": one_hour_ago}
    }).sort("timestamp", 1)

    return list(cursor)

def load_photo_message(msg):
    pass

def load_text_message(msg):
    return Message(msg.get("username"), msg.get("text"))

def handle_message(message):
    save_message(message)

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if f"@{BOT_USERNAME.lower()}" not in text.lower():
        return

    messages = get_last_hour_messages(chat_id)
    output = []
    for msg in messages:
        if msg.get("type") == "photo":
            pass # TODO
        else:
            output.append(load_text_message(msg))
