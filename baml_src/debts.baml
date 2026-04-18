class Message {
  user_name string
  text string
  reply_to Message? @description(#"The message this message is replying to, if any"#)
}

class Debt {
  debtor string @description(#"The person who owes money"#)
  creditor string @description(#"The person who should receive money"#)
  amount float @description(#"The amount of money owed"#)
  reason string? @description(#"Short reason or evidence from the chat for why this debt was extracted"#)
}

class Question {
  question string
}

function ExtractDebts(messages: Message[], normalized_names: string[]) -> Debt[] {
  client OpenRouterDebtExtractor
  prompt #"
    {{ _.role("system") }}
    You will receive a chat history between multiple users. Your task is to extract all the debts mentioned in the chat since the separator.
    Extract them into a list of debts, where each debt has a debtor, a creditor and an amount.
    Try to understand the conversation and extract the debts, but don't make assumptions or add depts that are not clearly implied.

    There will be a separator marking the point above which all dept conversation has been processed.
    The messages before this point are only info for better understanding those after (reciepts etc...).
    Not all messages are relevant for the debts.

    You are also given a list of normalized known participant names. Some entries may include usernames in brackets.
    Prefer assigning debtor and creditor by their names exactly from that list whenever the message likely refers to one of those people.
    Never use the usernames as the debtor or creditor, use it only for context.

    The bracketed username is only extra identity context so you know who is who.
    When a normalized entry contains a username in brackets, prefer the main person name as the debtor or creditor output, not the bracketed username alone.
    Sometimes the normalized names might be missing. Default to the mentioned name in the message in that case.

    Sometimes you will recieve a reply to a message. If it implies a debt was paid back (meaning the money got returned),
    add the exact same debt but with the debtor and creditor switched and the same amount.

    We will be processing the payments afterwards, so no need to simplify or merge the debts.
    Always include a short reason for each extracted debt, based on the relevant message(s).

    {{ _.role("user") }}
    Normalized names:
    {% for name in normalized_names %}
    - {{ name }}
    {% endfor %}

    Messages:
    {% for message in messages %}
    - {{ message }}
    {% endfor %}

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
    normalized_names ["Alice (@alice)", "Bob", "Peter (@peter)"]
  }
}
