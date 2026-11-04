"""Terminal chat with the Empório da Música agent.

    python main.py            # chat
    python main.py --debug    # also show each tool call
"""

import argparse
import json

from src.agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the Empório da Música agent.")
    parser.add_argument("--debug", action="store_true", help="show tool calls")
    parser.add_argument("--model", help="override LLM_MODEL")
    args = parser.parse_args()

    agent = Agent.from_env(model=args.model)
    print(f"Empório da Música · {agent.model}  (type 'sair' to quit)\n")

    while True:
        try:
            text = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"sair", "exit", "quit"}:
            break
        if not text:
            continue
        answer = agent.reply(text)
        if args.debug:
            for call in agent.trace:
                print(f"  ↳ {call.name}({json.dumps(call.arguments, ensure_ascii=False)})")
                print(f"    {json.dumps(call.result, ensure_ascii=False)[:300]}")
        print(f"\nEmpório: {answer}\n")


if __name__ == "__main__":
    main()
