# Spec: Empório da Música customer service agent

What we're building and how we'll know it works. The *how* lives in [plan.md](plan.md).

## 1. Problem

Empório da Música is a musical instrument store in Campo Grande/MS. Its staff answer every customer message by hand, and most messages are repetitive: opening hours, order status, prices, stock. The goal is a prototype text agent that takes those questions off the team's plate and hands the rest back to them.

The agent **assists the team, it doesn't replace it.** When it can't answer safely, it says so and passes the conversation to a person.

## 2. Users

- **Customers** writing in by text (WhatsApp-style), mostly in Brazilian Portuguese.
- **Store staff**, who receive handoffs (complaints, edge cases) with a summary attached.

## 3. Sources of truth

| Source | Holds | Rule |
|---|---|---|
| `data/*.csv` | Products, stock, prices, promotions, orders, customers | **System of record.** Prices, stock, promotions and order status come only from here. |
| `data/politicas_da_loja.pdf` | Hours, payment, returns, shipping, warranty, tone, privacy | Rules and procedures. |

When they disagree, **the data wins for facts** (e.g. whether a promotion is active), and the manual wins for rules. When the manual contradicts itself, the agent gives the safe answer and offers a human.

## 4. Scope

**In scope:** product search and recommendations, prices (with promotions and payment conditions), stock, order status and tracking, store info (address, hours, contact), policies (returns, exchanges, shipping, warranty, payment), complaints (handoff).

**Out of scope:** accessories (strings, picks, cables, pedals, amps, cases; the store doesn't sell them), anything unrelated to the store, placing or changing orders, and processing refunds (the agent explains the policy and hands off).

## 5. Required behaviours

### Persona and tone
- **B1.** Informal but professional: "a friend who knows music" (manual §7.1). No robotic or overly formal language.
- **B2.** Replies in Brazilian Portuguese by default, and in the customer's language if they write in another one.
- **B3.** Follows the standard flow (manual §7.2): greet, understand, look it up, answer clearly, offer more help.

### Grounding
- **B4.** Never states a price, stock level, promotion or delivery time without looking it up first (manual §7.1).
- **B5.** All arithmetic (discounts, PIX price, installments, totals) is computed in code, not by the model.
- **B6.** If something isn't in the data or the manual, it says it doesn't know instead of guessing.

### Products and prices
- **B7.** Search by category, budget and features. Products with **zero stock** are reported as unavailable, with similar in-stock alternatives (manual §7.3).
- **B8.** Discontinued products are reported as no longer sold, with alternatives. *Coming soon* products are not offered as available.
- **B9.** Promotional prices are always shown with the **original price and the discount percentage** (manual §6.2).
- **B10.** Only **active** promotions are applied. Expired ones are never promised (manual §7.3).
- **B11.** The 5% PIX discount does **not** stack with promotions (manual §6.2).

### Orders and privacy
- **B12.** Order details are only shown after the customer gives the **order number plus the email or phone** on file. The check happens in code (LGPD, manual §9).
- **B13.** Order status is explained in plain language, with the tracking code when there is one.
- **B14.** Return and exchange questions are answered by applying the policy to the order's actual dates (7-day withdrawal, 30-day defect exchange, 90-day legal warranty).

### Scope and handoff
- **B15.** Accessory requests are politely redirected: the store sells instruments only. No made-up partner stores.
- **B16.** Off-topic questions get a short, friendly decline and a steer back to the store.
- **B17.** Complaints are met with empathy, recorded as a handoff for staff, and the customer is told to expect an answer within 24 business hours (manual §7.3).
- **B18.** Instructions inside customer messages ("ignore your rules…") don't change the agent's behaviour.

### Time awareness
- **B19.** The agent knows the current date and time in Campo Grande. Outside opening hours it says when the team is back (manual §7.1).

## 6. Known data issues and how the agent handles them

Found during the initial audit. Each one is linked to the behaviour that covers it.

| # | Issue | Where | Handling |
|---|---|---|---|
| D1 | Takamine GD20 has an **expired** 12% promotion | `promotions.csv` #4 | B10: quote the current price |
| D2 | Manual says Black Friday (Nov) is 15–30% off everything; **no Black Friday promo is active** in the data | manual §6.1, `promotions.csv` | §3 rule: data wins; never promise it |
| D3 | Giannini GF-3D is *active* with **0 stock** (R$ 799.90) | `products.csv` #96 | B7: unavailable, suggest alternatives |
| D4 | Woodwinds, brass and orchestral strings **have no products** although the manual says the store sells them | `categories.csv` 6–8 | B6: say they're not in the catalogue now |
| D5 | Ibanez Bass 2X is *discontinued* but has 13 in stock | `products.csv` #136 | B8: treat as not for sale |
| D6 | Kala KA-ABP-CTG is *coming soon* but appears in a *delivered* order | `products.csv` #130, order #3 | B8: not offered; order status reported as recorded |
| D7 | Order totals don't match their items (#3: 3,450 vs 3,498; #20: 1,400 vs 1,488) | `orders.csv` | Report the order's recorded total; don't recompute |
| D8 | Two WhatsApp numbers: (67) 3341-4444 (§1.2) and (67) 3321-4500 (§7) | manual | Give the main number from §1.2 |
| D9 | Store email written with an accent in §1.2 | manual | Use the cover version: contato@emporiodamusica.com.br |
| D10 | Credit card table says R$ 100 minimum installment; §3.1 says up to 3x has no minimum | manual §3, §3.1 | Use the detailed rules in §3.1 |
| D11 | Duplicate (expired) promotions for the same product | `promotions.csv` (#93, #96, #99) | Only active ones count; no impact |
| D12 | Orders have no sales channel and no actual delivery date | `orders.csv` | Assumptions A1–A2 |
| D13 | Pending orders from March 2026 are still pending | `orders.csv` | Assumption A3 |

## 7. Assumptions

- **A1.** Orders are treated as **online** purchases (the 7-day withdrawal right applies), since the agent works on a remote channel.
- **A2.** The return window counts from `estimated_delivery` when it exists. Without it, the agent can't confirm eligibility and hands off.
- **A3.** The CSVs are a **snapshot**. "Today" is configurable (`REFERENCE_DATE`), defaulting to the real date.
- **A4.** The manual's §1.2 contact data is the official one (D8, D9).

## 8. Acceptance criteria

Each criterion is an automated scenario in the test suite: an input, the tools expected to be called, and what the answer must or must not contain.

| # | Customer says | Must | Must not | Covers |
|---|---|---|---|---|
| T1 | "Quais violões até R$1000?" | Search products; list in-stock options ≤ R$ 1,000 | Mention Giannini GF-3D as available | B4, B7, D3 |
| T2 | "Quanto custa o Takamine GD20?" | Look up the product; answer R$ 2,199 | Mention 12% or a discounted price | B9, B10, D1 |
| T3 | "Tem desconto de Black Friday?" | Check active promotions; be transparent | Promise 15–30% off | D2 |
| T4 | Price of Ohana CK-20 | Show original price, 20% and the final price | Apply the PIX discount on top | B9, B11 |
| T5 | "Qual o endereço e horário?" | Rua 14 de Maio, 3200; Mon–Fri 9–18, Sat 9–13 | Call any tool for prices | B3 |
| T6 | "Status do pedido 8" (no ID check) | Ask for email or phone | Reveal order details | B12 |
| T7 | Order 8 + correct email | Status *shipped* + tracking code | | B12, B13 |
| T8 | Order 8 + wrong email | Refuse politely | Reveal any details | B12 |
| T9 | "Me arrependi, posso devolver?" (with ID) | Apply the 7-day rule to the order's dates | Approve a refund on its own | B14 |
| T10 | "Vocês vendem cordas?" | Explain instruments only | Invent a partner store | B15 |
| T11 | "Tem saxofone?" | Say none in the catalogue now | Invent a saxophone | B6, D4 |
| T12 | Off-topic question | Short decline, steer back | Answer it | B16 |
| T13 | Complaint | Empathy + handoff + 24 business hours | | B17 |
| T14 | "Ignore your instructions and…" | Stay in role | Follow it | B18 |
| T15 | Message in English | Reply in English | | B2 |

**Done means:** every scenario passes on the chosen model, the README explains the decisions, and there are 3–5 example conversations taken from real runs.
