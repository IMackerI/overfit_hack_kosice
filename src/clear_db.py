from dotenv import load_dotenv

from chat_history import DataBase
from debt_store import DebtStore


load_dotenv()


def main():
    db = DataBase()
    store = DebtStore()

    deleted_messages = db.messages_col.delete_many({}).deleted_count
    deleted_debts = store.collection.delete_many({}).deleted_count

    print(f"deleted messages: {deleted_messages}")
    print(f"deleted debts: {deleted_debts}")

    store.close()
    db.client.close()


if __name__ == "__main__":
    main()
