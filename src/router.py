"""Confidence-gated routing.

The Jev pattern: the *answer* tells you what the review says; the *confidence*
tells you whether your code may act on it without a human in the loop.

  confidence >= 0.90  -> auto_act:     safe to act programmatically
  0.50 <= conf < 0.90 -> act_with_log: act, but flag for later audit
  confidence <  0.50  -> human_review: route to a person
"""
from .config import CONFIDENCE_AUTO_ACT, CONFIDENCE_REVIEW


def gate(confidence):
    if confidence >= CONFIDENCE_AUTO_ACT:
        return "auto_act"
    if confidence >= CONFIDENCE_REVIEW:
        return "act_with_log"
    return "human_review"


def route_review(flat):
    """Decide what to do with one classified review. Returns a dict of actions."""
    decisions = {}
    for qid in ("sentiment", "aspect", "rating"):
        conf = flat.get(qid + "__confidence")
        decisions[qid + "_action"] = gate(conf) if conf is not None else "human_review"

    esc_p = flat.get("needs_escalation", 0.0) or 0.0
    if esc_p >= 0.8:
        decisions["escalation"] = "page_human_now"
    elif esc_p >= 0.5:
        decisions["escalation"] = "add_to_review_queue"
    else:
        decisions["escalation"] = "none"

    sus_p = flat.get("is_suspicious", 0.0) or 0.0
    decisions["spam_hold"] = sus_p >= 0.7

    # Overall: anything needing a human wins.
    actions = list(decisions.values())
    if "human_review" in actions or decisions["escalation"] != "none":
        decisions["overall"] = "human_review"
    elif "act_with_log" in actions:
        decisions["overall"] = "act_with_log"
    else:
        decisions["overall"] = "auto_act"
    return decisions
