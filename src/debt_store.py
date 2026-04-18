import logging
import os
from collections import defaultdict
from datetime import UTC, datetime

from pymongo import MongoClient

from baml_client.types import Debt


EPSILON = 1e-9
DEFAULT_MONGODB_URI = "mongodb://localhost:27017"
DEFAULT_MONGODB_DB = "overfit_hack_kosice"
DEFAULT_MONGODB_COLLECTION = "debts"

logger = logging.getLogger(__name__)


class DebtStore:
    def __init__(
        self,
        uri: str | None = None,
        db_name: str | None = None,
        collection_name: str = DEFAULT_MONGODB_COLLECTION,
    ):
        self.client = MongoClient(
            uri or os.getenv("MONGODB_URI", DEFAULT_MONGODB_URI),
            serverSelectionTimeoutMS=3000,
        )
        self.collection = self.client[
            db_name or os.getenv("MONGODB_DB", DEFAULT_MONGODB_DB)
        ][collection_name]
        logger.info(
            "debt store initialized db=%s collection=%s",
            self.collection.database.name,
            self.collection.name,
        )

    def add_debt(self, debt: Debt) -> None:
        if debt.amount <= EPSILON or debt.debtor == debt.creditor:
            return

        self.collection.insert_one(
            {
                "debtor": debt.debtor,
                "creditor": debt.creditor,
                "amount": debt.amount,
                "created_at": datetime.now(UTC),
            }
        )
        logger.info(
            "stored debt debtor=%s creditor=%s amount=%s",
            debt.debtor,
            debt.creditor,
            debt.amount,
        )

    def add_debts(self, debts: list[Debt]) -> None:
        documents = [
            {
                "debtor": debt.debtor,
                "creditor": debt.creditor,
                "amount": debt.amount,
                "created_at": datetime.now(UTC),
            }
            for debt in debts
            if debt.amount > EPSILON and debt.debtor != debt.creditor
        ]
        if not documents:
            return

        self.collection.insert_many(documents)
        logger.info("stored debts count=%s", len(documents))

    def get_simplified_debts(self) -> list[Debt]:
        debts = [
            Debt(
                debtor=document["debtor"],
                creditor=document["creditor"],
                amount=float(document["amount"]),
            )
            for document in self.collection.find(
                {},
                {"_id": 0, "debtor": 1, "creditor": 1, "amount": 1},
            )
        ]
        logger.info("loaded raw debts count=%s", len(debts))
        simplified = self._simplify(debts)
        logger.info("simplified debts count=%s", len(simplified))
        return simplified

    @staticmethod
    def _simplify(debts: list[Debt]) -> list[Debt]:
        balances: dict[str, float] = defaultdict(float)
        for debt in debts:
            balances[debt.debtor] -= debt.amount
            balances[debt.creditor] += debt.amount

        debtors: list[list[str | float]] = []
        creditors: list[list[str | float]] = []

        for name, balance in balances.items():
            if balance < -EPSILON:
                debtors.append([name, -balance])
            elif balance > EPSILON:
                creditors.append([name, balance])

        simplified: list[Debt] = []
        debtor_index = 0
        creditor_index = 0

        while debtor_index < len(debtors) and creditor_index < len(creditors):
            debtor_name = str(debtors[debtor_index][0])
            debtor_amount = float(debtors[debtor_index][1])
            creditor_name = str(creditors[creditor_index][0])
            creditor_amount = float(creditors[creditor_index][1])

            settled = min(debtor_amount, creditor_amount)
            simplified.append(
                Debt(
                    debtor=debtor_name,
                    creditor=creditor_name,
                    amount=settled,
                )
            )

            debtors[debtor_index][1] = debtor_amount - settled
            creditors[creditor_index][1] = creditor_amount - settled

            if float(debtors[debtor_index][1]) <= EPSILON:
                debtor_index += 1
            if float(creditors[creditor_index][1]) <= EPSILON:
                creditor_index += 1

        return simplified

    def close(self) -> None:
        logger.info("closing debt store client")
        self.client.close()
