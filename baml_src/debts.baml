class Message {
  user_name string
  text string
}

class Debt {
  debtor string
  creditor string
  amount float
}

function ExtractDebts(messages: Message[]) -> Debt[] {
  client OpenRouterDebtExtractor
  prompt #"
    {{ _.role("system") }}
    Extract debts from chat messages.

    Rules:
    - Return one debt per payment obligation mentioned.
    - Repeated debts are allowed. Avoid doing arithmetic by yourself.
    - debtor is the person who owes money.
    - creditor is the person who should receive money.
    - Only include debts with a clear amount.

    {{ _.role("user") }}
    {% for message in messages %}
    - {{ message }}
    {% endfor %}

    {{ ctx.output_format }}
  "#
}

test ExtractDebtsSimple {
  functions [ExtractDebts]
  args {
    messages [
      {
        user_name: "Alice",
        text: "I paid 20 euros for Peter"
      }
      {
        user_name: "Alice",
        text: "Peter owes me 20"
      }
      {
        user_name: "Bob",
        text: ""
      }
    ]
  }
}
