class Message {
  user_name string
  text string
  reply_to Message? @description(#"The message this message is replying to, if any"#)
}

class Debt {
  debtor string @description(#"The person who owes money"#)
  creditor string @description(#"The person who should receive money"#)
  amount float @description(#"The amount of money owed"#)
}

class Question {
  question string
}

function ExtractDebts(messages: Message[], normalized_names: string[]) -> Debt[] {
  client OpenRouterDebtExtractor
  prompt #"
    {{ _.role("system") }}
    You recieve a chat history between multiple users. Your task is to extract all the debts mentioned in the chat.
    Extract them into a list of debts, where each debt has a debtor, a creditor and an amount.
    Infer from what they are talking about who owes money to whom and how much. All in
    Only messages since the last tag of the bot are relevant. The messages before that have already been processed.
    Not all messages are relevant for the debts.

    You are also given a list of normalized known participant names.
    Prefer assigning debtor and creditor names exactly from that list whenever the message likely refers to one of those people.
    Only use a completely different name if the chat clearly refers to someone not represented by the normalized names.

    Sometimes you will recieve a reply to a message that implies a debt was paid back.
    In that case, add the exact same debt but with the debtor and creditor switched and the same amount.

    Rules:
    - Repeated debts are allowed. Avoid doing arithmetic by yourself.

    {{ _.role("user") }}
    Normalized names:
    {% for name in normalized_names %}
    - {{ name }}
    {% endfor %}

    Messages:
    {% for message in messages %}
    - {{ message }}
    {% endfor %}

    Don't forget to exclude the messages before the last tag of the bot from the debts.

    {{ ctx.output_format }}
  "#
}


function ExtractImage(receipt: image) -> string {
  client OpenRouterDebtExtractor
  prompt #"
    {{ _.role("system") }}
    You are a part of a payment processing system.
    Your task is to extract all the relevant information from the image.
    If the image is a receipt, extract it as a list of items with prices and the total, the shop name, date ...
    For anything else just describe and extract text.
    
    {{ _.role("user") }}
    Extract info from this image:
    {{ receipt }}

    {{ ctx.output_format }}
  "#
}

test ImageReceiptTest {
  functions [ExtractImage]
  args {
    receipt { url "https://i.redd.it/adzt4bz4llfc1.jpeg"}
  }
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
        text: "I owe Bob 10 euros"
      }
      {
        user_name: "Bob",
        text: "Who payed for the pizza?"
      }
      {
        user_name: "Peter",
        text: "I paid the pizza for everyone, it was 30 euros. We can split it equally."
      }
    ]
    normalized_names ["Alice", "Bob", "Peter"]
  }
}
