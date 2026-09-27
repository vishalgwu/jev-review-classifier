"""Batch-classify reviews from a CSV.

Usage:
    export TYPESAFE_API_KEY="..."
    python -m src.classify --input data/sample_reviews.csv --output results.json

Input CSV needs at least a `review_text` column.
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client import classify_review, flatten  # noqa: E402
from src.router import route_review  # noqa: E402
from src.config import COST_PER_MTOK_INPUT_USD  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Multi-attribute review classifier (Jev)")
    ap.add_argument("--input", default="data/sample_reviews.csv")
    ap.add_argument("--output", default="results.json")
    args = ap.parse_args()

    with open(args.input, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    results, total_tokens, total_latency = [], 0, 0.0
    for r in rows:
        review_id = r.get("review_id", "?")
        print(f"[{review_id}] classifying...", flush=True)
        response, latency_ms = classify_review(r["review_text"])
        flat = flatten(response)
        flat["review_id"] = review_id
        flat["review_text"] = r["review_text"]
        flat["latency_ms"] = round(latency_ms, 1)
        flat["routing"] = route_review(flat)
        total_tokens += flat.get("input_tokens", 0)
        total_latency += latency_ms
        print(f"  -> sentiment={flat['sentiment']} ({flat['sentiment__confidence']}), "
              f"aspect={flat['aspect']} ({flat['aspect__confidence']}), "
              f"rating={flat['rating__label']}, route={flat['routing']['overall']}, "
              f"{latency_ms:.0f}ms")
        results.append(flat)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    n = len(results)
    cost = total_tokens / 1_000_000 * COST_PER_MTOK_INPUT_USD
    print(f"\nDone: {n} reviews -> {args.output}")
    print(f"Avg latency: {total_latency / n:.0f} ms | "
          f"Total input tokens: {total_tokens} | Est. cost: ${cost:.4f}")


if __name__ == "__main__":
    main()
