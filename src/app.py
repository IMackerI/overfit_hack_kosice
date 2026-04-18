import logging
from threading import Thread

from flask import Flask, request

from bot import handle_message
from config import WEBHOOK_SECRET

logger = logging.getLogger(__name__)

app = Flask(__name__)


def run_async(name, handler, payload):
    def runner():
        try:
            logger.info("background task started: %s", name)
            handler(payload)
            logger.info("background task finished: %s", name)
        except Exception:
            logger.exception("background task failed: %s", name)

    Thread(target=runner, daemon=True, name=name).start()


@app.route("/", methods=["GET"])
def home():
    logger.debug("healthcheck")
    return "Bot is running"


@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        logger.warning("webhook called without json body")
        return "no data"

    logger.info("webhook update keys=%s", sorted(data.keys()))

    if "message" in data:
        message = data["message"]
        logger.info(
            "dispatching message update chat_id=%s message_id=%s",
            message.get("chat", {}).get("id"),
            message.get("message_id"),
        )
        run_async("handle_message", handle_message, message)

    return "ok"


if __name__ == "__main__":
    app.run(port=5001)
