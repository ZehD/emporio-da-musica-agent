"""Record the example conversations in conversations/ from real agent runs.

    python -m scripts.record_conversations

Each conversation is a scripted list of customer messages. The agent's
replies and tool calls are whatever the model actually produced.
"""

import json
import os
from pathlib import Path

from src.agent import Agent

OUT = Path(__file__).resolve().parent.parent / "conversations"

CONVERSATIONS = [
    {
        "file": "01-catalog-search.md",
        "title": "Catalogue search on a budget",
        "note": "A beginner asks for acoustic guitars up to R$ 1,000. The agent searches the catalogue "
                "instead of answering from memory, leaves out the Giannini GF-3D (active but 0 in stock), "
                "and the PIX price and installments come from code, not from the model.",
        "reference_date": "2026-03-25",
        "messages": [
            "Oi! Tô começando a tocar agora, quais violões vocês têm até R$1000?",
            "Qual desses você indicaria pra quem tá começando? E quanto fica no PIX?",
        ],
    },
    {
        "file": "02-expired-promo-and-out-of-stock.md",
        "title": "Expired promotion, Black Friday and an out-of-stock item",
        "note": "The Takamine GD20 (a sample question from the brief) has an expired 12% promotion. "
                "The manual says Black Friday is in November, but no Black Friday promotion is active in the data. "
                "The agent quotes the current price and doesn't promise any discount. "
                "Then the customer asks for an item that's out of stock, and the agent offers in-stock alternatives.",
        "reference_date": "2026-11-03",
        "messages": [
            "Quanto custa o Takamine GD20?",
            "Mas ele não tava com 12% de desconto? E na Black Friday, vai ter desconto?",
            "Entendi. E o Giannini GF-3D, vocês têm?",
        ],
    },
    {
        "file": "03-return-request.md",
        "title": "Applying the return policy to a real order",
        "note": "The non-trivial case. The customer wants to return a purchase. The agent asks for the order number "
                "and the email on file before showing anything (privacy check done in code), looks up the order, "
                "reads the return policy, and works out with the customer whether they're within the 7-day window. "
                "It doesn't approve the refund itself: it hands the case to the team with a ticket.",
        "reference_date": "2026-02-05",
        "messages": [
            "Oi, me arrependi da minha compra. Posso devolver?",
            "Pedido 6, meu e-mail é gabriel.araujo@jmail.com",
            "Recebi no dia 1º. Tá na caixa, com tudo, nem cheguei a usar.",
        ],
    },
    {
        "file": "04-out-of-scope.md",
        "title": "Accessories, an empty category and an off-topic question",
        "note": "The store sells instruments only. Strings and amplifiers are politely redirected, without "
                "inventing partner stores. The manual says the store sells wind instruments, but there are "
                "none in the catalogue, so the agent says so instead of making one up. "
                "An off-topic question gets a short, friendly decline.",
        "reference_date": "2026-03-25",
        "messages": [
            "Vocês vendem encordoamento e amplificador?",
            "E saxofone, tem?",
            "Beleza. Aproveitando, quem ganhou o jogo do Operário ontem?",
        ],
    },
    {
        "file": "05-english-late-order-complaint.md",
        "title": "In English: a late order turns into a complaint",
        "note": "The customer writes in English, so the agent answers in English. The order is verified "
                "with the email on file. It shipped but is weeks past its estimated delivery date. "
                "When the customer complains, the agent responds with empathy, opens a handoff ticket "
                "for the team, and gives the 24-business-hour response time from the manual.",
        "reference_date": "2026-03-25",
        "messages": [
            "Hi! I ordered a ukulele, order 8, and it still hasn't arrived. My email is anacarol.ferreira@coldmail.com",
            "This is ridiculous, it was supposed to be here weeks ago. I want to talk to someone.",
        ],
    },
]


def render(conv: dict, model: str, turns: list) -> str:
    lines = [
        f"# {conv['title']}",
        "",
        f"> **What this shows:** {conv['note']}",
        ">",
        f"> Model: `{model}` · Store date: {conv['reference_date']} · Recorded from a real run "
        "(`python -m scripts.record_conversations`).",
        "",
    ]
    for message, answer, trace in turns:
        lines += [f"**Cliente:** {message}", ""]
        if trace:
            lines += ["<details><summary>Tool calls</summary>", "", "```"]
            for call in trace:
                lines.append(f"{call.name}({json.dumps(call.arguments, ensure_ascii=False)})")
                lines.append(f"  → {json.dumps(call.result, ensure_ascii=False)[:400]}")
            lines += ["```", "", "</details>", ""]
        lines += [f"**Empório:** {answer}", "", "---", ""]
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for conv in CONVERSATIONS:
        os.environ["REFERENCE_DATE"] = conv["reference_date"]
        agent = Agent.from_env()
        turns = []
        for message in conv["messages"]:
            answer = agent.reply(message)
            turns.append((message, answer, list(agent.trace)))
        (OUT / conv["file"]).write_text(render(conv, agent.model, turns), encoding="utf-8")
        print(f"wrote conversations/{conv['file']}")


if __name__ == "__main__":
    main()
