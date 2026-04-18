import os
from datetime import datetime, timezone

from pymongo import MongoClient


DEFAULT_MONGODB_URI = "mongodb://localhost:27017"
DEFAULT_MONGODB_DB = "telegram_bot"


class DataBase:
    def __init__(self, uri: str | None = None, db_name: str | None = None):
        self.client = MongoClient(
            uri or os.getenv("MONGODB_URI", DEFAULT_MONGODB_URI),
            serverSelectionTimeoutMS=3000,
        )
        self.db = self.client[db_name or os.getenv("MONGODB_DB", DEFAULT_MONGODB_DB)]
        self.messages_col = self.db["messages"]

    def save_message(self, message):
        doc = {
            "chat_id": message["chat"]["id"],
            "user_id": message["from"]["id"],
            "from_bot": False,
            "username": message["from"].get("username"),
            "timestamp": datetime.now(timezone.utc),
        }

        # text message
        if "text" in message:
            doc["type"] = "text"
            doc["text"] = message["text"]

        # TODO what if more photos?
        elif "photo" in message:
            doc["type"] = "photo"

            # Telegram sends multiple sizes → last one is highest quality
            photo = message["photo"][-1]

            doc["file_id"] = photo["file_id"]
            doc["caption"] = message.get("caption", "")

        self.messages_col.insert_one(doc)


    def get_recent_messages(self, chat_id, limit=50):
        cursor = (
            self.messages_col.find({"chat_id": chat_id})
            .sort("timestamp", -1)
            .limit(limit)
        )

        return list(reversed(list(cursor)))
    
    def find_one(self, pred):
        return self.messages_col.find_one(pred)
