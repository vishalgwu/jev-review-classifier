"""Thin wrapper around the TypeSafe SDK.

One call sends the review (state) plus ALL questions; Jev answers every
question in parallel and returns typed answers with probabilities and
confidence scores.
"""
import time

from typesafe_sdk import TypeSafeClient

from .config import JEV_MODEL, get_api_key
from .schema import build_questions


def classify_review(review_text, questions=None, model=None, timeout=60.0):
    """Classify one review. Returns (sdk_response, latency_ms)."""
    get_api_key()  # fail fast with a clear message if the key is missing
    questions = questions or build_questions()
    t0 = time.perf_counter()
    with TypeSafeClient() as client:
        response = client.system_one(
            state={"review": review_text},
            questions=questions,
            model=model or JEV_MODEL,
            timeout=timeout,
        )
    latency_ms = (time.perf_counter() - t0) * 1000
    return response, latency_ms


def flatten(response):
    """Convert an SDK response into a plain dict (one row per review)."""
    row = {"model": getattr(response, "model", None)}

    for qid, ans in (getattr(response, "choices", None) or {}).items():
        row[qid] = ans.choice
        row[qid + "__confidence"] = round(float(ans.confidence), 4)
        row[qid + "__probs"] = {k: round(float(v), 4) for k, v in dict(ans.probabilities).items()}

    for qid, ans in (getattr(response, "scores", None) or {}).items():
        score = float(ans.score)
        row[qid] = round(score, 2)
        row[qid + "__confidence"] = round(float(ans.confidence), 4)
        legend = {int(k): v for k, v in dict(ans.legend or {}).items()}
        # nearest labelled level, e.g. 2.91 -> "3 stars"
        row[qid + "__label"] = legend.get(int(round(score)), legend.get(int(score)))
        row[qid + "__probs"] = {legend.get(int(k), k): round(float(v), 4)
                                for k, v in dict(ans.probabilities).items()}

    for qid, ans in (getattr(response, "nouls", None) or {}).items():
        row[qid] = round(float(ans.noul), 4)

    usage = getattr(response, "usage", None)
    if usage is not None:
        row["input_tokens"] = int(getattr(usage, "input_tokens", 0) or 0)
        row["output_tokens"] = int(getattr(usage, "output_tokens", 0) or 0)
    return row
