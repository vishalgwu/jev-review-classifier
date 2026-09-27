"""Evaluate predictions against ground truth.

Usage:
    python -m src.evaluate --truth data/sample_reviews.csv --preds results.json

Reports per-attribute accuracy, rating MAE, escalation detection, plus
latency and cost summary.
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import COST_PER_MTOK_INPUT_USD  # noqa: E402


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def main():
    ap = argparse.ArgumentParser(description="Evaluate review classifier")
    ap.add_argument("--truth", default="data/sample_reviews.csv")
    ap.add_argument("--preds", default="results.json")
    args = ap.parse_args()

    truth = {r["review_id"]: r for r in csv.DictReader(open(args.truth, encoding="utf-8"))}
    preds = {p["review_id"]: p for p in json.load(open(args.preds, encoding="utf-8"))}
    ids = [i for i in truth if i in preds]
    print(f"Evaluating {len(ids)} reviews\n")

    for attr, col in (("sentiment", "true_sentiment"), ("aspect", "true_aspect")):
        ok = sum(1 for i in ids if str(preds[i][attr]).lower() == truth[i][col].strip().lower())
        print(f"{attr:10s} accuracy: {ok}/{len(ids)} = {pct(ok, len(ids))}")

    # Note: Jev's Score runs on the legend *index* scale (0-4), so +1 -> stars.
    errs = [abs(round(preds[i]["rating"]) + 1 - int(truth[i]["true_rating"])) for i in ids]
    print(f"{'rating':10s} MAE: {sum(errs) / len(errs):.2f} stars "
          f"(exact: {pct(sum(1 for e in errs if e == 0), len(ids))})")

    for attr, col in (("needs_escalation", "true_needs_escalation"),
                      ("is_suspicious", "true_is_suspicious")):
        ok = sum(1 for i in ids
                 if (preds[i][attr] >= 0.5) == (truth[i][col].strip() == "1"))
        print(f"{attr:10s} accuracy: {ok}/{len(ids)} = {pct(ok, len(ids))} (threshold p>=0.5)")

    lat = [preds[i]["latency_ms"] for i in ids]
    toks = sum(preds[i].get("input_tokens", 0) for i in ids)
    print(f"\nAvg latency: {sum(lat) / len(lat):.0f} ms "
          f"(min {min(lat):.0f} / max {max(lat):.0f})")
    print(f"Est. cost: ${toks / 1_000_000 * COST_PER_MTOK_INPUT_USD:.4f} "
          f"for {toks} input tokens (output free)")


if __name__ == "__main__":
    main()
