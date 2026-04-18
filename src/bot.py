import requests

from baml_client import b
from baml_client.types import Debt, Message
from chat_history import DataBase
from config import BOT_TOKEN
from debt_store import DebtStore

BOT_USERNAME = "hack_kosice_bot"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

db = DataBase()
debt_store = DebtStore()


def load_photo_message(msg):
    caption = msg.get("caption", "")
    if not caption:
        return None
    return Message(user_name=msg.get("username") or "unknown", text=f"[photo] {caption}")


def load_text_message(msg):
    return Message(
        user_name=msg.get("username") or "unknown",
        text=msg.get("text") or "",
    )


def get_chat_history(chat_id, limit=50):
    output = []
    for msg in db.get_recent_messages(chat_id, limit=limit):
        loaded_message = None
        if msg.get("type") == "text":
            loaded_message = load_text_message(msg)
        elif msg.get("type") == "photo":
            loaded_message = load_photo_message(msg)

        if loaded_message is not None:
            output.append(loaded_message)

    return output


def handle_message(message):
    db.save_message(message)
    text = message.get("text", "")

    if f"@{BOT_USERNAME.lower()}" not in text.lower():
        return

    chat_id = message["chat"]["id"]
    messages = get_chat_history(chat_id)

    if not messages:
        send_message(chat_id, "No recent messages found.")
        return

    debts = b.ExtractDebts(messages)
    debt_store.add_debts(debts)
    summarize_debts(debt_store.get_simplified_debts(), chat_id)


def handle_reaction(update):
    reaction = update.get("message_reaction")

    if not reaction:
        return

    chat_id = reaction["chat"]["id"]
    message_id = reaction["message_id"]

    msg = db.find_one({
        "chat_id": chat_id,
        "message_id": message_id,
        "from_bot": True,
    })

    if not msg:
        return
    
    parts = text.split()

    creditor = parts[0]
    debtor = parts[4]
    amount = float(parts[6])
    
    debt_store.add_debt(Debt(creditor, debtor, -amount))


def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    requests.post(url, json=payload, timeout=10)


def demand_payment(debt: Debt, chat_id):
    text = f"{debt.debtor} owes {debt.creditor} {debt.amount:.2f}"
    send_message(chat_id, text)


def summarize_debts(debts, chat_id):
    if not debts:
        send_message(chat_id, "No debts found.")
        return

    for debt in debts:
        demand_payment(debt, chat_id)




