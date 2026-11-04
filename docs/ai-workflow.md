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

**Next:** first commits, then code.
