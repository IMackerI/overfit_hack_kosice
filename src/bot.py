import requests
from config import BOT_TOKEN
from baml_client import b
from baml_client.types import Message, Debt
from chat_history import DataBase

BOT_USERNAME = "hack_kosice_bot"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

db = DataBase()

def load_photo_message(msg):
    url = f"{TELEGRAM_API}/getFile"
    params = {"file_id": file_id}

    response = requests.get(url, params=params).json()

    if response.get("ok"):
        return Message(msg.get("username"), b.ExtractImage(response["result"]["file_path"]))

    return None

def load_text_message(msg):
    return Message(msg.get("username"), msg.get("text"))

def get_chat_history(chat_id):
    output = []
    for msg in db.get_recent_messages(chat_id):
        if msg.get("type") == "text":
            output.append(load_text_message(msg))
        if msg.get("type") == "photo":
            output.append(load_photo_message(msg))


def handle_message(message):
    db.save_message(message)
    text = message.get("text", "")

    # If tagged, recap history
    if f"@{BOT_USERNAME.lower()}" in text.lower():
        chat_id = message["chat"]["id"]
        messages = get_chat_history(chat_id)
        debts = b.ExtractDebts(messages)
        summarize_debts(debts)

    #TODO remove all database entries?
    # TODO volaj najeaky analyzer
    

def handle_reaction(update):
    reaction = update.get("message_reaction")

    if not reaction:
        return
    
    chat_id = reaction["chat"]["id"]
    message_id = reaction["message_id"]
    user_id = reaction["user"]["id"]

    msg = db.find_one({
        "chat_id": chat_id,
        "message_id": message_id,
        "from_bot": True
    })

    # ignore if it is reaction to other people's messages
    if not msg:
        return


    # TODO volaj najeaky analyzer

    
def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


def summarize_debts(debts, chat_id):

    debt_map = dict()
    for d in debts:
        if d.creditor not in debt_map:
            debt_map[d.creditor] = 0
        if d.debtor not in debt_map:
            debt_map[d.debtor] = 0
        
        debt_map[d.creditor] += d.amount
        debt_map[d.debtor] -= d.amount

    for (k,v) in debt_map:
        pass


