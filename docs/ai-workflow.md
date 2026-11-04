# How I worked with AI on this case

A running log of how I used an AI coding assistant to build this project. The brief asks how candidates use these tools, so instead of a summary written at the end, I'm keeping notes as I go.

**Tool:** Claude Code (VS Code extension), running Claude Opus 5.5.

**Ground rules I set for myself**

- **I own the decisions.** The assistant reads, audits, drafts and implements. I choose, review every diff, and should be able to explain every line.
- **Context before code.** The assistant gets the same picture I have, not just the task.
- **Spec before code.** Nothing gets implemented until it's written down as a requirement with a way to check it.

---

## Day 1 · Tue, Nov 3, 2026 (evening)

### Starting with the full context

I created an empty project folder and dropped in the original materials as received: the case zip (brief PDF, the store's policy manual, six CSVs). In the first message I also pasted the recruiter's email, so the assistant knew the role, the five-stage process, the deadline rule, the submission format and the "answers in English" requirement.

The reason: an assistant that only sees the task PDF optimizes for the task. One that also sees the email understands the constraints around it: how it will be evaluated, by when, and in what language.

### First pass: read and audit, no code

I asked for a brainstorm, not an implementation. The assistant extracted the zip (the accented folder names broke `unzip`, so it fell back to Python), read the brief and the 8-page manual, and cross-checked the CSVs against each other and against the manual.

That audit found inconsistencies that end up shaping the design:

- The **Takamine GD20**, one of the brief's own sample questions, has an **expired** 12% promotion.
- The manual says Black Friday means 15–30% off in November. It's November, and **no Black Friday promotion is active** in the data.
- An "active" acoustic guitar with **zero stock** falls inside the "violões até R$1000" sample question.
- Three categories the manual says the store sells (woodwinds, brass, orchestral strings) **have no products**.
- Two order totals don't match their items, and a *delivered* order contains a *coming soon* product.
- The manual has **two different phone numbers** and **conflicting installment rules**.
- Orders are linked to customers' personal data, and the manual has an LGPD section, so **order lookups need identity checks**.

Each finding points to a specific file and row, so it can be checked instead of taken on trust. None of these will be fixed by patching the prompt. They become acceptance criteria in the spec.

The same pass also flagged two process risks outside the code: an ambiguous deadline (a national holiday fell on the second day) and a git identity pointing at the wrong account (more on that below). Small things, but exactly the kind that sink a submission.

### Keeping context between sessions

The project context (brief summary, deadline, submission rules, conventions) is saved in Claude Code's project memory, so each new session starts from the same picture instead of re-reading everything.

### Choosing the method: Spec-Driven Development

Why SDD fits working with an AI assistant:

- **The spec is the contract.** Assistants are fast and confident, and without a written target they fill gaps with plausible guesses. A short spec gives something fixed to check their output against.
- **Decisions are written before code.** The same text later becomes the README's "technical decisions" section.
- **Acceptance criteria become the evals.** Each finding from the audit turns into a test scenario. For example: *asks the GD20's price → current price, no expired discount.*
- **Tasks map to commits.** The git history follows the plan.

I kept it lean on purpose: three short files, not a process.

| File | Answers |
|---|---|
| `docs/spec.md` | What and why: users, scope, expected behaviours, acceptance criteria |
| `docs/plan.md` | How: architecture, model, tools, trade-offs |
| `docs/tasks.md` | An ordered checklist; each item is one commit |

### Setting up the repo, with the right account

I created the public repo empty, right at the start, so GitHub's timeline covers the whole process and not only the finished result.

I keep separate personal and work accounts (GitHub, deploy platforms). My global `CLAUDE.md`, the instructions file Claude Code loads in every project, maps which account belongs to which kind of project. It also requires the assistant to check the active account before any push or deploy. That rule paid off here: my machine's default git identity is the work one. Before creating anything, the assistant switched the GitHub CLI to my personal account and set a repo-local git identity, so every commit in this repo is authored with my personal identity.

It's a small setup that lets me hand an AI assistant real git and deploy access without worrying about it acting under the wrong account.

### Language: English deliverables, a Portuguese-speaking agent

The recruiter's email asks for all answers in English, while the brief, the data and the manual are in Portuguese. I drew the line like this:

- **Everything I deliver is in English:** README, docs, code, comments, commit messages.
- **The store's name stays as is.** "Empório da Música" is the client's brand, so the repo is `emporio-da-musica-agent`. Translating it would be renaming the client.
- **The agent speaks Brazilian Portuguese by default**, because the store's customers do, and the manual asks for an informal, friendly tone.
- **It answers in the customer's language** if they write in English or Spanish. That costs almost nothing with an LLM, and it makes the demo readable for reviewers who don't speak Portuguese.

The example conversations follow the same rule: in Portuguese, each with a short English note on top saying what it demonstrates, plus one in another language to show the switch.

### Provider: OpenRouter behind an OpenAI-compatible client

The brief leaves the model and provider open. I chose the OpenAI Python SDK pointed at OpenRouter, with the server address, key and model set in `.env`:

- **Reviewers can run it with whatever key they have.** OpenRouter, OpenAI directly, or a local model through Ollama all work by changing settings, not code.
- **The model is chosen by evidence.** With one key, the same test scenarios can run against several models, and the pick is based on pass rate, cost and latency.
- **No framework.** One SDK and a short tool-calling loop that's easy to read end to end.

I used a temporary key with a small credit limit for development. It lives only in a git-ignored `.env`.

### Writing the spec, and dropping a false finding

I organised the materials into `data/` with plain file names. The case brief stays out of the public repo, since it's the company's material.

Then we wrote [spec.md](spec.md) from the audit: required behaviours, each data issue mapped to how the agent handles it, explicit assumptions, and 15 acceptance scenarios that will become the test suite.

While checking the audit row by row, one finding didn't hold up. The first pass had reported a city name ("Ponta Porã") stored with two different spellings. Looking at the raw bytes, it was just Windows line endings, plus a missing newline on the last row. It isn't a data problem, so it didn't go into the spec. That's the reason every finding has to point to a file and row before it counts.

### The plan: fixed tools, and choosing not to use RAG

I used the assistant as a sparring partner on the architecture. I asked two questions: should we load the data into a database and give the agent a tool to query it, and is there room for a simple RAG?

On the first, I already leaned towards fixed tools over free-form queries, and the discussion confirmed it. Text-to-SQL would let the model read the customer table and do its own arithmetic. Narrow tools keep the privacy check and the math in code.

On RAG, the deciding factor was the shape of the data. The operational data is small and structured, so it needs exact lookups, not similarity search. The manual is short and already split into numbered sections, so the agent can fetch a whole section by name. Adding embeddings would add a way to fail without adding anything. The brief lists RAG among possible approaches; knowing when *not* to use it is part of the answer.

Both decisions, and when I'd revisit them, are in [plan.md](plan.md).

### Building: tools first, then the loop, then the tests

The build order followed the plan: the manual converted to markdown sections, the data layer, the five tools, the prompt and the loop, then the test suite. Each step was checked before the next one and committed separately.

Some things I only learned by running the code:

- **Smoke-testing the tools caught a search bug before any model was involved.** Searching for "violão" also returned a ukulele, whose description mentions the word. Now category words in the search text become a category filter.
- **The first test run failed 2 of 15, and only one failure was the agent's fault.** The English message (T15) got a Portuguese reply, because every tool result is in Portuguese and pulled the model along. A clearer language rule at the top of the prompt fixed it.
- **The other failure was my spec's.** On the return request (T9), the agent didn't simply confirm eligibility. It noticed the data only has an *estimated* delivery date, said the customer was probably within the 7 days, and asked for the actual receipt date before handing off to the team. That's better than what I'd specified. I changed spec assumption A2 and the test's judging question, not the agent.
- **Same thing on T5:** one model checked the manual for the opening hours. The test had forbidden *any* tool, but what matters is that it doesn't call *data* tools for a store-info question, so I narrowed the rule.

The lesson I keep relearning: when a test fails, first ask whether the agent was wrong or the test was. Changing a test to make it pass is only legitimate when you can write down why the original expectation was wrong, which is what the notes above are for.

### A bug the tests didn't catch, found by using it

Chatting with the agent by hand, I asked about a saxophone. It correctly said there were none, then offered "a flute or a clarinet instead". There are no wind instruments in the catalogue at all. The search had come back empty, and the model filled the gap with the manual's description of what the store sells. The test for this scenario (T11) had passed, because its judging question only checked that no saxophone was invented.

The assistant's first fix was to put a summary of which categories have stock into the system prompt, computed from the data each turn. It worked, but I pushed back: that's catalogue data living in the prompt, when our own rule is that facts come from tools. It also makes the prompt change whenever the data does, which works against prompt caching. My instinct was to reinforce the rule ("always check availability before offering"), maybe with an extra tool.

We landed on something between the two:
- **A stricter rule:** only offer products or product types that a tool returned in this conversation.
- **No new tool.** The empty search result now lists the categories that do have stock. The failure happens exactly when a search comes back empty, so that's where the information needs to be. Then the model doesn't have to remember a second tool at the moment it's most likely to improvise.
- **A stricter test:** T11 now fails if the answer offers any wind instrument.

Tests catch what you thought to check. Using the thing catches the rest, and every bug found that way becomes a new check.

### Going a step further: a small web UI

With the core done, I added a small web UI: streaming chat plus a run inspector showing, for each turn, the model, latency, time to first token, tokens and every tool call. The constraint I gave the assistant was the same as for the rest: simple code, grounded in the spec. That meant one FastAPI file and one HTML page with plain JavaScript, no build step, and no second agent loop: the existing loop now yields events, and everything else consumes them.

The inspector exists for the same reason as `--debug` in the terminal. With an agent, the interesting part is not the answer but *why* it gave it: which tool it picked, with what arguments, and what came back.

### Reading the conversations like a reviewer would

The example conversations are recorded from real runs, so I read every one before committing them, as if I were the reviewer. They looked fine at a glance and had two problems:

- **The expired promotion.** Asked "wasn't it 12% off?", the agent said it couldn't confirm a previous discount. It was being honest: my data layer threw expired promotions away, so it had never seen them. But manual §7.3 asks for the opposite: tell the customer the promotion *has ended*, and give the current price. Expired promotions now come back from `get_product` as a separate list ("ended"), never used for prices. The agent now says "that 12% offer has ended". In trying to keep the agent away from stale data, I had removed context it needed.
- **Promising what it can't do.** It offered to "let you know on WhatsApp when there's a promotion". It has no way to do that, and the store's privacy policy requires explicit consent for marketing messages. New rule: only offer actions the tools can actually perform; for anything else, offer the team.

Neither was caught by the tests, because both were things I hadn't thought to check. Reading the output is part of testing.

### Choosing the model with the tests

One OpenRouter key made it cheap to compare models on the same 15 scenarios. A full run of four models cost less than one US cent. Results are in the README.

**Next:** example conversations and the README.
