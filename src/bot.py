import logging
import time

import requests

from baml_client import b
from baml_client.types import Debt, Message
from chat_history import DataBase
from config import BOT_TOKEN
from debt_store import DebtStore

BOT_USERNAME = "hack_kosice_bot"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logger = logging.getLogger(__name__)

db = DataBase()
debt_store = DebtStore()


def load_photo_message(msg):
    url = f"{TELEGRAM_API}/getFile"
    params = {"file_id": msg["file_id"]}

    response = requests.get(url, params=params).json()

    if response.get("ok"):
        return Message(msg.get("username"), b.ExtractImage(response["result"]["file_path"]))

    return None

def load_text_message(msg):
    logger.debug("msg: " + str(msg))
    return Message(
        user_name=msg.get("username") or "unknown",
        text=msg.get("text") or "",
        reply_to=load_text_message(msg.get("reply_to_message")) if "reply_to_message" in msg else None
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

    logger.info("prepared chat history chat_id=%s count=%s", chat_id, len(output))
    return output


def handle_message(message):
    chat_id = message["chat"]["id"]
    message_id = message.get("message_id")
    text = message.get("text", "")
    logger.info(
        "handle_message start chat_id=%s message_id=%s has_text=%s",
        chat_id,
        message_id,
        bool(text),
    )

    db.save_message(message)

    if f"@{BOT_USERNAME.lower()}" not in text.lower():
        logger.info("message ignored because bot was not mentioned chat_id=%s message_id=%s", chat_id, message_id)
        return

    messages = get_chat_history(chat_id)

    if not messages:
        logger.warning("no recent messages found for chat_id=%s", chat_id)
        send_message(chat_id, "No recent messages found.")
        return

    start = time.monotonic()
    logger.info("starting BAML ExtractDebts chat_id=%s message_count=%s", chat_id, len(messages))
    debts = b.ExtractDebts(messages)
    logger.info(
        "finished BAML ExtractDebts chat_id=%s debt_count=%s duration_s=%.2f",
        chat_id,
        len(debts),
        time.monotonic() - start,
    )

    debt_store.add_debts(debts)
    simplified_debts = debt_store.get_simplified_debts()
    logger.info("summarizing debts chat_id=%s simplified_count=%s", chat_id, len(simplified_debts))
    summarize_debts(simplified_debts, chat_id)


def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    logger.info("sending telegram message chat_id=%s text=%r", chat_id, text)
    response = requests.post(url, json=payload, timeout=10)
    logger.info("telegram sendMessage status=%s", response.status_code)
    response_json = response.json()
    if response.ok and response_json.get("ok"):
        db.save_bot_message(response_json["result"])
    else:
        logger.warning("telegram sendMessage failed body=%s", response_json)


def demand_payment(debt: Debt, chat_id):
    logger.info(
        "demand_payment chat_id=%s debtor=%s creditor=%s amount=%s",
        chat_id,
        debt.debtor,
        debt.creditor,
        debt.amount,
    )
    text = f"{debt.debtor} owes {debt.creditor} {debt.amount:.2f}"
    send_message(chat_id, text)


def summarize_debts(debts, chat_id):
    logger.info("summarize_debts chat_id=%s count=%s", chat_id, len(debts))
    if not debts:
        send_message(chat_id, "No debts found.")
        return

    for debt in debts:
        demand_payment(debt, chat_id)




