from flask import Flask, request

from bot import handle_message, handle_reaction
from config import WEBHOOK_SECRET

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return "Bot is running"


@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data:
        return "no data"

    if "message" in data:
        handle_message(data["message"])

    if "message_reaction" in data:
        handle_reaction(data)

    return "ok"


if __name__ == "__main__":
    app.run(port=5001)
