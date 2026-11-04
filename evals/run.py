"""Run the acceptance scenarios against one or more models.

    python -m evals.run                                   # model from .env
    python -m evals.run --models anthropic/claude-haiku-5.5 openai/gpt-6-luna
"""

import argparse
import os
import time
import unicodedata

from src.agent import Agent

from .scenarios import SCENARIOS

DEFAULT_REFERENCE_DATE = "2026-03-25"  # last day covered by the data snapshot
JUDGE_MODEL = "anthropic/claude-haiku-5.5"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def judge(agent: Agent, question: str, customer: str, answer: str) -> bool:
    verdict = agent.client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        messages=[{"role": "user", "content":
                   f"Customer message:\n{customer}\n\nAssistant reply:\n{answer}\n\n"
                   f"Question: {question}\nAnswer only YES or NO."}],
    ).choices[0].message.content or ""
    return verdict.strip().upper().startswith("YES")


def run_scenario(model: str, s: dict) -> tuple[list[str], float, str]:
    os.environ["REFERENCE_DATE"] = s.get("reference_date", DEFAULT_REFERENCE_DATE)
    agent = Agent.from_env(model=model)
    start = time.time()
    answer = agent.reply(s["message"])
    elapsed = time.time() - start
    called = [c.name for c in agent.trace]
    text = norm(answer)

    failures = []
    for tool in s.get("tools", []):
        if tool not in called:
            failures.append(f"did not call {tool}")
    for tool in s.get("forbid_tools", []):
        if tool in called:
            failures.append(f"called {tool} but shouldn't")
    if s.get("no_tools") and called:
        failures.append(f"called {called} but shouldn't")
    for item in s.get("must", []):
        options = item if isinstance(item, tuple) else (item,)
        if not any(norm(o) in text for o in options):
            failures.append(f"missing '{options[0]}'")
    for item in s.get("must_not", []):
        if norm(item) in text:
            failures.append(f"contains '{item}'")
    if s.get("judge") and not judge(agent, s["judge"], s["message"], answer):
        failures.append("judge: NO")
    return failures, elapsed, answer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="*")
    parser.add_argument("--only", nargs="*", help="scenario ids, e.g. T2 T9")
    parser.add_argument("--repeat", type=int, default=1, help="runs per scenario (LLMs vary)")
    args = parser.parse_args()
    models = args.models or [Agent.from_env().model]
    scenarios = [s for s in SCENARIOS if not args.only or s["id"] in args.only] * args.repeat

    summary = []
    for model in models:
        print(f"\n=== {model}")
        passed, total_time = 0, 0.0
        for s in scenarios:
            try:
                failures, elapsed, answer = run_scenario(model, s)
            except Exception as exc:
                failures, elapsed, answer = [f"error: {exc}"], 0.0, ""
            total_time += elapsed
            ok = not failures
            passed += ok
            print(f"  {'PASS' if ok else 'FAIL'} {s['id']:<4} {elapsed:4.1f}s  {'; '.join(failures)}")
            if not ok and answer:
                print(f"         ↳ {answer[:200]!r}")
        summary.append((model, passed, len(scenarios), total_time / max(len(scenarios), 1)))

    print(f"\n{len(scenarios) // args.repeat} scenarios x {args.repeat} run(s)")
    print("\n| Model | Passed | Avg latency |\n|---|---|---|")
    for model, passed, total, latency in summary:
        print(f"| {model} | {passed}/{total} | {latency:.1f}s |")


if __name__ == "__main__":
    main()
