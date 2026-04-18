import logging
import time

import requests
from baml_py import Image

from baml_client import b
from baml_client.types import Debt, Message
from chat_history import DataBase, get_display_name, normalize_mentions
from config import BOT_TOKEN
from debt_store import DebtStore

BOT_USERNAME = "hack_kosice_bot"
BOUNDARY_TEXT = "--- ALL DEBTS BEFORE THIS POINT WERE ALREADY PROCESSED. ONLY EXTRACT NEW DEBTS BELOW. ---"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logger = logging.getLogger(__name__)

db = DataBase()
debt_store = DebtStore()


def resolve_user_name(msg):
    return get_display_name(msg) or get_display_name(msg.get("from")) or "unknown"


def format_name_for_llm(msg):
    name = resolve_user_name(msg)
    username = msg.get("username") or msg.get("from", {}).get("username")

    if name == "unknown":
        return None, False
    if username and username.lower() != name.lower():
        return f"{name} (@{username})", True
    return name, False


def collect_normalized_names(messages):
    names = {}

    def visit(msg):
        if not msg:
            return

        formatted_name, has_username = format_name_for_llm(msg)
        if formatted_name is not None:
            key = resolve_user_name(msg).lower()
            existing = names.get(key)
            if existing is None or (has_username and "(@" not in existing):
                names[key] = formatted_name

        reply_to_message = msg.get("reply_to_message")
        if reply_to_message:
            visit(reply_to_message)

    for msg in messages:
        visit(msg)

    return sorted(names.values())


def collect_username_map(messages):
    username_map = {}

    def visit(msg):
        if not msg:
            return

        username = msg.get("username") or msg.get("from", {}).get("username")
        display_name = resolve_user_name(msg)
        if username and display_name != "unknown":
            username_map[username.lower()] = display_name

        reply_to_message = msg.get("reply_to_message")
        if reply_to_message:
            visit(reply_to_message)

    for msg in messages:
        visit(msg)

    return username_map


def load_photo_message(msg, username_map=None):
    url = f"{TELEGRAM_API}/getFile"
    params = {"file_id": msg["file_id"]}

    response = requests.get(url, params=params, timeout=10).json()

    if not response.get("ok"):
        logger.warning("getFile failed for file_id=%s body=%s", msg.get("file_id"), response)
        return None

    file_path = response["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    extracted_text = b.ExtractImage(Image.from_url(file_url))

    return Message(
        user_name=resolve_user_name(msg),
        text=extracted_text,
        reply_to=load_text_message(msg.get("reply_to_message"), username_map) if "reply_to_message" in msg else None,
    )

def load_text_message(msg, username_map=None):
    logger.debug("msg: %s", msg)
    return Message(
        user_name=resolve_user_name(msg),
        text=normalize_mentions(msg.get("text") or "", msg.get("entities"), username_map),
        reply_to=load_text_message(msg.get("reply_to_message"), username_map) if "reply_to_message" in msg else None,
    )


def message_mentions_bot(msg):
    text = (msg.get("text") or msg.get("caption") or "").lower()
    bot_name = BOT_USERNAME.lower()
    return f"@{bot_name}" in text or bot_name in text


def split_messages_for_boundary(raw_messages, current_message_id):
    non_bot_messages = [msg for msg in raw_messages if not msg.get("from_bot")]

    previous_mention_index = None
    for index, msg in enumerate(non_bot_messages):
        if msg.get("message_id") == current_message_id:
            continue
        if message_mentions_bot(msg):
            previous_mention_index = index

    if previous_mention_index is None:
        return [], non_bot_messages

    return (
        non_bot_messages[: previous_mention_index + 1],
        non_bot_messages[previous_mention_index + 1 :],
    )


def build_baml_messages(processed_messages, relevant_messages, username_map=None):
    output = []

    for msg in processed_messages:
        loaded_message = None
        if msg.get("type") == "text":
            loaded_message = load_text_message(msg, username_map)
        elif msg.get("type") == "photo":
            loaded_message = load_photo_message(msg, username_map)

        if loaded_message is not None:
            output.append(loaded_message)

    output.append(Message(user_name="System", text=BOUNDARY_TEXT))

    for msg in relevant_messages:
        loaded_message = None
        if msg.get("type") == "text":
            loaded_message = load_text_message(msg, username_map)
        elif msg.get("type") == "photo":
            loaded_message = load_photo_message(msg, username_map)

        if loaded_message is not None:
            output.append(loaded_message)

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

    raw_messages = db.get_recent_messages(chat_id)
    non_bot_messages = [msg for msg in raw_messages if not msg.get("from_bot")]
    processed_messages, relevant_messages = split_messages_for_boundary(raw_messages, message_id)
    normalized_names = collect_normalized_names(non_bot_messages)
    username_map = collect_username_map(non_bot_messages)
    messages = build_baml_messages(processed_messages, relevant_messages, username_map=username_map)
    logger.info(
        "prepared chat history chat_id=%s raw_count=%s processed_count=%s relevant_count=%s baml_count=%s normalized_names=%s",
        chat_id,
        len(raw_messages),
        len(processed_messages),
        len(relevant_messages),
        len(messages),
        normalized_names,
    )

    if not relevant_messages:
        logger.warning("no recent messages found for chat_id=%s", chat_id)
        send_message(chat_id, "No recent messages found.")
        return

    start = time.monotonic()
    logger.info(
        "starting BAML ExtractDebts chat_id=%s message_count=%s normalized_name_count=%s",
        chat_id,
        len(messages),
        len(normalized_names),
    )
    debts = b.ExtractDebts(messages, normalized_names)
    logger.info(
        "finished BAML ExtractDebts chat_id=%s debt_count=%s duration_s=%.2f",
        chat_id,
        len(debts),
        time.monotonic() - start,
    )
    for debt in debts:
        logger.info(
            "extracted debt debtor=%s creditor=%s amount=%s reason=%r",
            debt.debtor,
            debt.creditor,
            debt.amount,
            debt.reason,
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




