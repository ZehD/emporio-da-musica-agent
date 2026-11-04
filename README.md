# Empório da Música: customer service agent

A prototype text agent for **Empório da Música**, a (fictional) musical instrument store in Campo Grande/MS. It answers the questions that take up the team's day (prices, stock, orders, opening hours, return rules) and hands everything else to a person.

The agent talks to customers in Brazilian Portuguese, or in whatever language they write in. Everything else in this repo is in English.

**Where to look**

| If you want… | Go to |
|---|---|
| To see it working | [conversations/](conversations/): 5 recorded conversations, with tool calls |
| What it must do, and the data issues I found | [docs/spec.md](docs/spec.md) |
| How it's built, and why | [docs/plan.md](docs/plan.md) |
| How I worked with an AI coding assistant | [docs/ai-workflow.md](docs/ai-workflow.md) |

---

## Running it

Requires Python 3.11+ and an API key for any OpenAI-compatible provider (OpenRouter by default).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your key in OPENROUTER_API_KEY
```

```bash
uvicorn web.app:app         # web chat at http://localhost:8000 ("Runs" opens the run inspector)
python main.py              # chat in the terminal
python main.py --debug      # also print every tool call and its result
python -m evals.run         # run the 15 acceptance scenarios
python -m scripts.record_conversations   # regenerate conversations/
```

**Provider settings** (`.env`):

| Variable | Default | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | | Also accepts `OPENAI_API_KEY` |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | Use `https://api.openai.com/v1` for OpenAI, `http://localhost:11434/v1` for Ollama |
| `LLM_MODEL` | `anthropic/claude-haiku-5.5` | Any model with tool calling |
| `REFERENCE_DATE` | today | Pin "today" (`YYYY-MM-DD`); the data is a snapshot |

---

## How it works

```
customer message → tool-calling loop (OpenAI SDK → OpenRouter)
                     │  the model picks a tool, the code runs it
                     ├─ search_products   catalogue search: category, budget, keywords
                     ├─ get_product       price, active promotion, PIX, installments, stock
                     ├─ get_order         order status, only after an identity check
                     ├─ get_policy        one whole section of the store manual
                     └─ handoff_to_human  ticket for the team (complaints, refunds, edge cases)
```

The CSVs are loaded into pandas at startup. The manual is converted once into [one markdown file per section](docs/policies/). The system prompt sets the persona and rules, plus the current date and time in Campo Grande, so the agent knows whether the store is open. Everything about the catalogue comes from tools: the agent may only offer products a tool returned, and an empty search lists the categories that do have stock, so it never offers an instrument type the store doesn't carry.

The loop streams events (text, tool calls, a run summary). The web UI shows them live, with a **run inspector**: latency, time to first token, tokens and every tool call for each turn.

About 700 lines of Python for the agent itself (plus tests and scripts), with no agent framework.

---

## Technical decisions

The full reasoning is in [docs/plan.md](docs/plan.md). In short:

**Fixed tools, not text-to-SQL.** The model chooses *which* tool to call. The code decides *what* comes back. That keeps three things out of the model's hands:
- **Privacy:** `get_order` returns nothing unless the order number matches the email or phone on file. The check is in code, so no prompt can talk its way past it.
- **Arithmetic:** promotion prices, the 5% PIX discount (not stackable with promotions), installment limits and date differences are all computed in Python.
- **Variance:** each tool is a plain function, easy to test.

**No RAG.** The operational data is small and structured: it needs exact filters, not similarity search. The manual is 8 pages and already split into numbered sections, so `get_policy` returns a whole section chosen by name. No chunking, no embeddings, no vector store, and no risk of retrieving the wrong fragment. I'd add retrieval with a catalogue in the thousands (hybrid keyword + embedding search over descriptions) or manuals hundreds of pages long.

**Provider-agnostic.** The plain OpenAI SDK with a configurable base URL runs on OpenRouter, OpenAI or a local Ollama model without code changes. One key also made it cheap to choose the model with data (below).

**No framework.** The loop is about 100 lines. LangChain or LangGraph would add abstraction without adding capability at this size. They'd make sense with multi-step workflows, persisted state or approval steps.

**Prompt strategy.** A short system prompt: persona and tone from the manual (§7.1), language rule, live store status, store basics that every conversation needs, and 10 numbered rules. Each rule traces back to a behaviour in the spec. Tool descriptions say *when* to use each tool, which is where most routing decisions are actually made.

**Conversation history** is kept in memory for the session. That's what a chat needs; persisting it is listed under limitations.

---

## Choosing the model: tested, not guessed

The 15 acceptance scenarios in [evals/scenarios.py](evals/scenarios.py) come straight from [spec §8](docs/spec.md#8-acceptance-criteria). Each one checks:
- which tools were called;
- what the answer must and must not contain;
- for things text matching can't catch, a yes/no question to an LLM judge.

I ran the full suite **3 times per model** (LLMs vary run to run) on four inexpensive models with tool calling:

| Model | Passed (15 × 3) | Avg latency | Price per 1M tokens (in / out) |
|---|---|---|---|
| google/gemini-3.8-flash | **45/45** | 5.9s | $0.83 / $4.12 |
| **anthropic/claude-haiku-5.5** (default) | 44/45 | 3.4s | $0.10 / $0.50 |
| deepseek/deepseek-v4.1-flash | 44/45 | **2.6s** | $0.04 / $0.50 |
| openai/gpt-6-luna | 42/45 | 5.4s | $0.10 / $0.50 |

**Why Haiku and not the top scorer.** One failure in 45 is within noise, so I looked at *which* failures each model had:
- **Haiku's** one miss was replying in Portuguese to an English message: annoying, but harmless.
- **Gemini** passed everything, but it's ~75% slower and ~8× the token price. It's the pick if accuracy matters more than cost; it's a one-line `.env` change.
- **DeepSeek** is the fastest and cheapest, but on the return request it treated the *estimated* delivery date as the actual one. With refunds, that's the kind of slip that matters.
- **GPT-6 Luna** missed the return scenario on all 3 runs.

This comparison was run before the last two prompt rules (ended promotions, and only offering actions the agent can perform). After adding them, I re-checked the default model on the affected scenarios.

All four models, 3 runs each, cost **under US$ 1** in total, so testing before choosing costs almost nothing.

---

## Data issues found, and how they're handled

The data and the manual contain deliberate traps. All 13 are in [spec §6](docs/spec.md#6-known-data-issues-and-how-the-agent-handles-them). The ones that matter most:

- **The Takamine GD20 (a sample question in the brief) has an *expired* 12% promotion.** The agent quotes the current price.
- **The manual says Black Friday is 15–30% off in November, and it's November, but no Black Friday promotion is active in the data.** Rule: the data wins on facts. No discount is promised.
- **The Giannini GF-3D is "active" but has 0 stock.** It's left out of searches and shown as sold out, with alternatives.
- **The manual says the store sells wind and orchestral instruments, but those categories are empty.** The agent says so instead of inventing products.
- **Some order totals don't match their items, and a *delivered* order contains a *coming soon* product.** The agent reports the recorded total and never recomputes it.
- **The manual has two WhatsApp numbers and two conflicting installment rules.** The decisions are documented in the spec.

## Assumptions

From [spec §7](docs/spec.md#7-assumptions):
1. Orders are treated as **online** purchases, so the 7-day withdrawal right applies.
2. The data has **no actual delivery date**. `estimated_delivery` is used as an estimate, and the agent confirms the real date with the customer.
3. The CSVs are a **snapshot**. `REFERENCE_DATE` pins "today"; the tests run at 2026-03-25, the end of the data.
4. The manual's §1.2 contact details are the official ones.

---

## Next improvement: tool results

I reviewed the tools against Anthropic's guidance on writing tools for agents.

**Naming is in line with it.** The tools have specific verb_noun names, unambiguous parameters, `enum` for fixed values, and descriptions that say *when* to call each tool. I didn't namespace the tools (e.g. `store_products_search`). That advice is for agents with many tools across several services; with five tools in one domain it adds noise. I'd add prefixes when a second system comes in, such as a carrier's tracking API.

**The tool results are where I'd invest next.** The guidance is to return meaningful context and make errors actionable: what went wrong, what valid input looks like, what to try next. Today:
- **Empty searches** list the categories with stock. They should also say *why* the search came back empty and what to try instead: repeat the filters used, give the cheapest in-stock option in that category, and mention sold-out matches.
- **Truncated searches** show 10 results without saying how many exist. They should say "showing 10 of 33; narrow it with `max_price` or `query`".
- **Internal codes** like `credit_12x` should come back as readable labels ("crédito em 12x").
- **Invalid arguments** return the raw exception text. They should say which parameter was wrong and what the valid values are.
- **Failed order checks** show where this guidance meets privacy. The result must never say *which* field didn't match, or it would reveal whether an order exists. It can still guide the agent: ask the customer to check both fields, and offer a handoff after two failed attempts.

Each change would be measured with the test suite before and after, like every other change in this project.

## Known limitations, and what I'd do with more time

- **Holidays.** The agent knows the weekly hours but not the holiday calendar. I'd add a holiday list for Campo Grande.
- **Handoff is a JSON file** in `handoffs/`. In production it would open a ticket in the store's helpdesk or WhatsApp inbox, with the conversation attached.
- **History is per session.** I'd persist it by phone number, so returning customers don't repeat themselves.
- **The tests are small (15 scenarios) and partly judged by an LLM.** I'd grow the set from real conversations, track pass rates over time, and run it in CI on every prompt change.
- **Data passes through OpenRouter.** For a real store under LGPD, I'd call the model provider directly (or self-host) under a data processing agreement, and keep customer data out of logs.
- **Search is keyword-based.** It's fine for 65 products. With thousands, I'd add hybrid search.
- **Order identity check** uses order number + email or phone. A real deployment on WhatsApp would use the sender's verified number instead.

---

## Use of AI coding assistants

I used **Claude Code** (VS Code extension) throughout, as a pair programmer that I directed. The full log, written as I worked, is in [docs/ai-workflow.md](docs/ai-workflow.md). In short:

- **Context first.** I gave it the brief, the data, the manual *and* the recruiter's email, so it worked with the same constraints I had.
- **Audit before code.** The first session was analysis only: cross-checking the CSVs against each other and against the manual. That's where the data issues above came from. Every finding had to cite a file and row. One that didn't hold up (a "duplicated" city that was really just line endings) was dropped.
- **Spec-driven.** The spec, plan and task order were written before any code. Each acceptance criterion became a test.
- **I made the decisions.** I used it to argue through architecture (fixed tools vs. text-to-SQL, RAG or not) and kept the parts I could defend.
- **Tests settle disagreements.** When a test failed, the first question was whether the agent or the test was wrong. Twice it was the test, and the log explains why each one changed.
- **Guardrails on the assistant too.** My global `CLAUDE.md` maps which accounts belong to personal vs. work projects, and requires a check before any push. Here it caught that my machine's default git identity was the wrong one before the first commit.

---

## Project layout

```
main.py                  terminal chat
web/                     web chat (FastAPI + one HTML page) with run inspector
src/
  data.py                load + clean the CSVs
  tools.py               the five tools and their schemas
  prompts.py             system prompt
  agent.py               tool-calling loop
  clock.py               "now" in Campo Grande (and REFERENCE_DATE)
evals/                   acceptance scenarios + runner
scripts/                 records the example conversations
conversations/           5 example conversations from real runs
data/                    store CSVs and manual (as received)
docs/
  spec.md · plan.md · ai-workflow.md
  policies/              the manual, one markdown file per section
```
