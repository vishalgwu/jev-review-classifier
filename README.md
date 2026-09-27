# Multi-Attribute E-Commerce Review Classifier (Jev)

A hands-on project on **Jev** by TypeSafe AI — the
"System-1" decision model that returns *decisions, not text*.

One product review goes in as the **state**; five typed **questions** are
evaluated **in parallel in a single API call**, each returning a value plus
calibrated probabilities and a confidence score your code can branch on.

## How it works

```
review text (state)
      │
      ▼
┌─────────────┐   ┌──────────────┐   ┌────────────┐   ┌──────────────────┐   ┌───────────────┐
│  sentiment  │   │    aspect    │   │   rating   │   │ needs_escalation │   │ is_suspicious │
│   (Choice)  │   │   (Choice)   │   │  (Score)   │   │      (Noul)      │   │     (Noul)     │
└─────────────┘   └──────────────┘   └────────────┘   └──────────────────┘   └───────────────┘
      │                  │                 │                   │                    │
      └──────────────────┴─────────────────┴───────────────────┴────────────────────┘
                                         ▼
                              confidence-gated routing
                    ┌──────────────┬──────────────┬──────────────┐
                    │   auto_act   │ act_with_log │ human_review │
                    │  conf ≥ .90  │ .50–.90      │   conf < .50 │
                    └──────────────┴──────────────┴──────────────┘
```

Because every output is schema-constrained, Jev *cannot* return malformed
results — no JSON parsing, no prompt-injection-shaped answers.

## Setup

```bash
cd jev-review-classifier
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # typesafe-sdk, pandas, streamlit
export TYPESAFE_API_KEY="your_key"     # get one at https://typesafe.ai
```

## Usage

**1. Classify the sample reviews**
```bash
python -m src.classify --input data/sample_reviews.csv --output results.json
```

**2. Evaluate against ground truth**
```bash
python -m src.evaluate --truth data/sample_reviews.csv --preds results.json
```
Reports per-attribute accuracy, rating MAE, escalation/spam detection,
average latency, and estimated cost (input tokens only — output is free).

**3. Live demo UI**
```bash
streamlit run app.py
```
Paste any review and watch all five attributes resolve with confidence bars
and the routing decision.

## Project layout

| Path | What it is |
|---|---|
| `src/schema.py` | The question schema — **the heart of the project**. Add/remove typed questions here. |
| `src/client.py` | SDK wrapper: one `system_one` call per review + `flatten()` to plain dicts. |
| `src/router.py` | Confidence-gated routing (`auto_act` / `act_with_log` / `human_review`). |
| `src/classify.py` | Batch CLI: CSV in → `results.json` out, with latency + cost summary. |
| `src/evaluate.py` | Accuracy / MAE / latency / cost report vs ground truth. |
| `data/sample_reviews.csv` | 12 labeled reviews to start from. |
| `app.py` | Streamlit demo. |

## Extending it

- **More attributes**: add a `Choice`/`Score`/`Noul` in `src/schema.py` — no
  retraining, no prompt engineering. This is "generalized classification".
- **Your own data**: swap in a CSV with a `review_text` column (+ `true_*`
  columns if you want eval).
- **Agentic routing**: use the `aspect`/`needs_escalation` answers to route
  reviews into different agent workflows (refund bot, human queue, spam filter).
- **CI/CD**: add a GitHub Actions workflow running `src/evaluate.py` on a
  held-out set as a quality gate before deploy.

## Notes

- Model defaults to `jev-latest` (override with `JEV_MODEL`).
- Vendor pricing at time of writing: $0.042 / 1M input tokens, output free;
  expect ~70–500 ms per call. Measure your own — don't trust vendor peaks.
- Known Jev limits (per TypeSafe's docs): literal reading of negations, no
  math/counting, context rot on very large states. Keep questions atomic.
