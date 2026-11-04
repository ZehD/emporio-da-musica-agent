# Plan: how the agent is built

The *what* is in [spec.md](spec.md). This file covers the *how* and the reasons behind it.

## Architecture

```
customer message
      │
      ▼
┌─────────────────────────────┐
│ Agent loop (tool calling)   │  system prompt: persona, rules,
│ OpenAI SDK → OpenRouter     │  store basics, current time
└─────────────┬───────────────┘
              │ the model picks a tool; code runs it
      ┌───────┼────────────┬──────────────┬───────────────┐
      ▼       ▼            ▼              ▼               ▼
 search_   get_       get_order      get_policy     handoff_to_
 products  product    (+ identity    (one manual    human
                       check)        section)       (ticket file)
      └───────┴────────────┘              │
              │                           │
        pandas over data/*.csv     docs/policies/*.md
```

One loop: send the conversation and tool definitions to the model, run whatever tools it asks for, send the results back, and repeat until it answers in text.

## Key decisions

### 1. Fixed tools, not text-to-SQL
The agent never writes queries. It calls a small set of tools with typed parameters, and the code behind each tool decides what data comes back.

- **Privacy is enforced in code.** `get_order` returns nothing unless the order number and the email or phone match. A prompt can't talk its way past that.
- **Math is in code.** Promotion prices, the PIX discount, the non-stacking rule and installment options are computed by the tools. The model only puts them into words.
- **Testable.** Each tool is a plain function with predictable output.

Text-to-SQL would answer more kinds of questions, but for a customer-facing agent the risk isn't worth it: it could read the customer table, do arithmetic itself, and produce different queries for the same question.

### 2. No RAG
The brief lists RAG among the possible approaches. We chose not to use it, because the data here isn't suited to it:

- **The operational data is structured and small** (65 products, 20 orders). It needs exact filters and lookups, not similarity search.
- **The manual is short and already split into 10 numbered sections.** It's converted once to markdown, one file per section. `get_policy(section)` returns a whole section, chosen by name from a fixed list. No chunking, no embeddings, no vector store, so no risk of retrieving the wrong fragment. It also shows up in the tool-call trace, so you can see when the agent checked the policy.

**When RAG would earn its place:** a catalogue in the thousands (hybrid keyword + embedding search over product descriptions), or manuals hundreds of pages long (chunked retrieval, measured by whether it finds the right passage).

### 3. Data in pandas, behind the tools
The CSVs are loaded into pandas at startup and cleaned once (types, line endings, statuses). Every data access goes through the tools, so moving to the store's real database later means changing one module.

### 4. Provider: OpenAI SDK pointed at OpenRouter
Server address, key and model are set in `.env`. That works with OpenRouter, OpenAI directly, or a local model, so reviewers can use whatever key they have. The model is chosen by running the test scenarios on a shortlist and comparing pass rate, cost and latency.

### 5. No agent framework
The loop is about 60 lines on the plain SDK. A framework (LangChain, LangGraph) would add abstraction without adding capability at this size. It would make sense with multi-step workflows, persisted checkpoints or human approval steps.

### 6. Interface: terminal chat
`python main.py` starts a chat; `--debug` prints each tool call and its result. A script replays scripted conversations and saves them as markdown in `conversations/`.

### 7. Conversation history
Kept in memory for the session, which is what a chat needs. Saving it across sessions (by customer phone number, for example) is listed under "with more time".

### 8. Time awareness
The current date and time in Campo Grande (America/Campo_Grande) goes into the system prompt each turn. `REFERENCE_DATE` can override "today", since the data is a snapshot (spec assumption A3).

## Tools

| Tool | Parameters | Returns |
|---|---|---|
| `search_products` | `query?`, `category?`, `max_price?`, `in_stock_only=true` | Up to 10 matches: name, price, stock, active promotion, final price |
| `get_product` | `name_or_id` | Full details, specs, active promotion, final price, PIX price, installment options; or "not found" with close matches |
| `get_order` | `order_id`, `email_or_phone` | Status, dates, items, total, tracking; or a refusal if the contact doesn't match |
| `get_policy` | `section` (fixed list) | The full text of that manual section |
| `handoff_to_human` | `reason`, `summary` | Ticket ID; the ticket is written to `handoffs/` |

## Project layout

```
data/               store CSVs + manual PDF (as received)
docs/policies/      manual converted to markdown, one file per section
src/
  data.py           load + clean the CSVs
  tools.py          the five tools + their JSON schemas
  prompts.py        system prompt
  agent.py          the tool-calling loop
main.py             terminal chat
evals/              acceptance scenarios (spec §8) + runner
conversations/      example transcripts
```

## Testing

`evals/scenarios.py` holds the 15 scenarios from spec §8. For each one, the runner checks:
- **which tools were called** (deterministic);
- **what the answer must and must not contain** (simple text checks).

The same suite runs on each shortlisted model. Results go in the README.
