# How Jev Works — and How This Project Uses It

A complete explanation of the Jev model, the ideas behind it, and exactly how
each piece of this project maps to those ideas. Written for someone who wants
to *understand* the system, not just run it.

---

## Part 1 — What Jev is

### The one-sentence version
**Jev is a model that returns decisions, not text.** You give it a *state*
(the material to judge) and a set of *typed questions*; it returns structured
answers your code can use directly — no text generation, no JSON parsing.

### System-1 vs System-2 thinking
The name comes from Daniel Kahneman's *Thinking, Fast and Slow*:

| | System-1 | System-2 |
|---|---|---|
| Style | Fast, automatic, intuitive | Slow, deliberate, reasoning |
| Example | Recognizing a friend's face | Solving a math proof |
| AI analogue | **Jev**: instant classification | **LLMs**: step-by-step reasoning, chain-of-thought |

Traditional LLMs (GPT, Claude, …) are System-2-ish: they generate tokens one
at a time, "thinking out loud." That is powerful but slow and expensive when
all you need is a *judgment* — "is this review positive?", "which team owns
this ticket?" Jev is built for exactly those judgments: fast, structured,
calibrated decisions. (The product name is also a nod to the economist
William Stanley Jevons and the *Jevons paradox*: make each decision radically
cheaper, and people will automate decisions they never bothered with before.)

### Why not just use an LLM with structured output?
You can — but you pay three taxes:

1. **Latency tax**: an LLM streams tokens one-by-one. Ten questions answered
   via ten prompts (or one long prompt) takes seconds.
2. **Cost tax**: you pay for every output token it generates.
3. **Reliability tax**: the model can return malformed JSON, extra prose, or
   an option you never listed. Your code needs defensive parsing.

Jev eliminates all three: it is **non-autoregressive** (it does not generate
tokens sequentially), its outputs are **schema-constrained** (it can only pick
from options *you* defined — it literally cannot hallucinate a new label),
and output tokens are **free**.

---

## Part 2 — The three primitives: Choice, Score, Noul

Every Jev question is one of three typed primitives. Think of them as the
`if`-statements of AI — the smallest units of machine judgment:

### 1. `Choice` — "pick one option"
```json
{
  "sentiment": {
    "type": "choice",
    "choice": "positive",
    "probabilities": {"positive": 0.86, "neutral": 0.14, "negative": 0.0},
    "confidence": 0.79
  }
}
```
- `choice`: the winning option.
- `probabilities`: the full distribution over *your* options — useful for
  "top-2" logic, disagreement detection, or beam search.
- `confidence`: how sure the model is (derived from the shape of the
  distribution). **This is the key architectural signal** — see Part 4.

### 2. `Score` — "rate on a rubric"
```json
{
  "rating": {
    "type": "score",
    "score": 2.91,
    "probabilities": {"0": 0.0, "1": 0.0, "2": 0.1, "3": 0.89, "4": 0.01},
    "legend": {"0": "1 star", "1": "2 stars", "2": "3 stars", "3": "4 stars", "4": "5 stars"},
    "confidence": 0.91
  }
}
```
- `score`: a continuous value on the legend's *index* scale (here 0–4, so
  2.91 ≈ "4 stars"). Add 1 to convert to 1–5 stars.
- `legend`: maps each index to its label. `probabilities` is keyed by index.

### 3. `Noul` — "yes/no, as a probability"
```json
{ "needs_escalation": { "type": "noul", "noul": 0.38 } }
```
- `noul`: P(yes), a number in [0, 1]. Threshold it in code (e.g. ≥ 0.5).
  ("Noul" is TypeSafe's name for a yes/no question.)

### The golden rule: keep questions atomic
Jev works best when each question asks **one specific, well-scoped thing** —
"the kind of judgment a knowledgeable person could make in a few seconds."
If a judgment needs extended reasoning or weighs multiple factors, decompose
it: ask each factor as its own question and combine them with logic in *your*
code. That keeps every evaluation reliable and puts the weighting where it
belongs — under your control, as coefficients, not buried in a prompt.

---

## Part 3 — How a request works (what actually happens)

### The API call
```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <TYPESAFE_API_KEY>
Content-Type: application/json
```
```json
{
  "model": "jev-latest",
  "state": {"review": "The headphones sound amazing... Shipping took 2 weeks though."},
  "questions": {
    "sentiment":        {"type": "choice", "instructions": "...", "criteria": {"positive": "...", "neutral": "...", "negative": "..."}},
    "aspect":           {"type": "choice", "instructions": "...", "criteria": {"none": "...", "price": "...", "quality": "...", "shipping": "...", "service": "..."}},
    "rating":           {"type": "score",  "instructions": "...", "criteria": ["1 star", "2 stars", "3 stars", "4 stars", "5 stars"]},
    "needs_escalation": {"type": "noul",   "instructions": "..."},
    "is_suspicious":    {"type": "noul",   "instructions": "..."}
  }
}
```

Three things to notice:

1. **`state` is the material under judgment.** It can be a string, an object,
   or an array. Here it's `{"review": "<text>"}` — naming the field gives the
   model structure to refer to.
2. **All five questions ride in ONE request** and are evaluated **in parallel,
   in isolation, against the same state**. Adding questions barely changes
   response time and does not degrade the others (no "context rot"). This is
   the *multi-question parallel sampling* advantage.
3. **`instructions` + `criteria` define the schema.** `criteria` maps each
   allowed option to a short description of what it means. The model can only
   ever return these options — schema-constrained output.

### What comes back
```json
{
  "model": "jev-1.13.0",
  "answers": {
    "sentiment":        {"type": "choice", "choice": "positive", "confidence": 0.79, "probabilities": {...}},
    "aspect":           {"type": "choice", "choice": "shipping", "confidence": 1.0,  "probabilities": {...}},
    "rating":           {"type": "score",  "score": 2.91, "confidence": 0.91, "legend": {...}, "probabilities": {...}},
    "needs_escalation": {"type": "noul",   "noul": 0.38},
    "is_suspicious":    {"type": "noul",   "noul": 0.02}
  },
  "usage": {"input_tokens": 439, "output_tokens": 121}
}
```
(This is a real response from this project's test run.) Every answer is keyed
by the question id *you* chose, so parsing is trivial: `answers["sentiment"]`.

### Under the hood (the 30-second version)
Jev is a **non-autoregressive decoder**: instead of predicting token after
token (like an LLM), it encodes the state once and evaluates all questions
against that encoding simultaneously. Conceptually, the classic "LM head"
(which predicts the next token) is replaced by **answer heads** that output
probability distributions over your closed option sets. That is why it is
fast (no sequential generation), cheap (output is free — there are no
generated tokens to bill), and structurally incapable of free-form
hallucination.

---

## Part 4 — Confidence: the second axis

Every `Choice` and `Score` answer carries a **confidence** score. The mental
model from TypeSafe's docs:

> *The answer tells you **what**; the confidence tells you **whether to act**.*

This project implements the recommended **confidence-gated routing** pattern
(`src/router.py`):

| Confidence | Action | Meaning |
|---|---|---|
| ≥ 0.90 | `auto_act` | Safe to act programmatically, no human needed |
| 0.50 – 0.90 | `act_with_log` | Act, but flag for later audit |
| < 0.50 | `human_review` | Route to a person — the model is unsure |

Two real examples from our test run show why this matters:

- A genuinely ambiguous review ("It's fine… nothing special") came back with
  sentiment confidence **0.49** → routed to `human_review` instead of being
  auto-tagged on a coin flip.
- The spam review ("BUY NOW BEST PRODUCT EVER!!!") was misclassified as
  *positive* sentiment — but the parallel `is_suspicious` question caught it
  at **0.97**, so the review was held anyway. One bad answer didn't sink the
  system because the questions are independent.

---

## Part 5 — How this project is organized (and why)

```
review text ──▶ schema.py ──▶ client.py ──▶ router.py ──▶ action
   (state)     (questions)   (one API    (confidence-
                               call)      gated routing)
```

| File | Role | The Jev idea it embodies |
|---|---|---|
| `src/schema.py` | Defines the 5 typed questions | **Atomic typed questions** — the entire "prompt engineering" of Jev lives here, as a schema, not prose |
| `src/client.py` | One `system_one()` call per review; `flatten()` normalizes answers | **Parallel evaluation** — all questions, one request, ~360 ms |
| `src/router.py` | `auto_act` / `act_with_log` / `human_review` | **Confidence as a second axis** |
| `src/classify.py` | Batch CLI: CSV → `results.json` | Putting the pipeline together |
| `src/evaluate.py` | Accuracy / MAE / latency / cost vs ground truth | Measuring, not trusting vendor benchmarks |
| `app.py` | Streamlit live demo | **Real-time UI** — one of Jev's headline use cases |
| `data/sample_reviews.csv` | 12 labeled reviews | Ground truth for honest evaluation |

### Measured results (12 reviews, live API)

| Metric | Result |
|---|---|
| sentiment accuracy | 91.7% (11/12) |
| aspect accuracy | 100% (12/12) |
| rating MAE | 0.33 stars (75% exact) |
| escalation detection | 91.7% |
| spam detection | 100% |
| avg latency | **361 ms** (min 286 / max 517) |
| total cost | **$0.0003** (7,675 input tokens @ $0.042/MTok; output free) |

The latency and cost numbers are the point of the Jevons-paradox bet: at a
fraction of a cent per decision, you can afford to run classification on
*every* review, *every* ticket, *every* agent tool-call — decisions you would
never have paid a frontier LLM to make.

---

## Part 6 — Honest limitations

No technology section is complete without these (several are acknowledged in
TypeSafe's own docs):

- **No reasoning.** Jev does not think step-by-step. If a judgment genuinely
  needs multi-hop reasoning, decompose it or escalate to an LLM.
- **Literal reading of negations**, no math/counting/date arithmetic.
- **Context rot on very large states** — keep the state focused.
- **Adversarial text in the state can steer answers** — treat untrusted input
  accordingly (which is partly why the `is_suspicious` question exists).
- **Benchmarks are vendor-run.** Treat the 80x–400x cost claims as the high
  end; independent field reports land lower (still large, ~18–25x). The
  `src/evaluate.py` harness exists so you can measure your own workload.
- **Black-box weights.** You get an API, not a model you can inspect or
  self-host (as of this writing).

---

## Part 7 — Where this goes next

Jev is not a replacement for LLMs — it is a **complement**: the fast decision
layer *in front of* the reasoning layer. The architecture TypeSafe envisions,
and the one this project demonstrates in miniature:

```
incoming text ──▶ Jev (fast, cheap, typed) ──▶ high confidence? ──▶ act
                                                    │
                                              low confidence? ──▶ LLM / human
```

For agentic workflows specifically: use Jev for tool routing (which tool does
this request need?), guardrails (is this action safe?), and real-time UI
updates — and reserve the big reasoning model for the steps that actually
need reasoning. That is the "System-1 + System-2" software architecture, and
this classifier is the smallest useful version of it.
