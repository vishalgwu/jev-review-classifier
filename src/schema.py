"""Question schema for the multi-attribute review classifier.

The core Jev idea: instead of one vague prompt, define small *atomic* typed
questions. Every question is evaluated in parallel against the same review
(state), in a single API call. Adding questions barely changes latency.

Question types:
  - Choice: pick one option from a closed set  -> choice, probabilities, confidence
  - Score:  rate against ordered levels        -> score, probabilities, confidence
  - Noul:   yes/no probability                 -> noul (0..1)

To extend the classifier, just add entries here; classify.py picks them up.
"""
from typesafe_sdk import Choice, Noul, Score


def build_questions():
    return {
        "sentiment": Choice(
            instructions="What is the overall sentiment of this product review?",
            criteria={
                "positive": "The reviewer is satisfied, praises the product, or would recommend it.",
                "neutral": "The reviewer is neither clearly satisfied nor dissatisfied; mixed or purely factual.",
                "negative": "The reviewer is dissatisfied, complains, or would not recommend it.",
            },
        ),
        "aspect": Choice(
            instructions=(
                "If the reviewer raises a problem, which aspect is it about? "
                "Choose 'none' if no problem or complaint is raised."
            ),
            criteria={
                "none": "No problem or complaint is raised.",
                "price": "Complaint about price, value for money, or cost.",
                "quality": "Complaint about product quality, defects, or durability.",
                "shipping": "Complaint about delivery speed, packaging, or logistics.",
                "service": "Complaint about customer service, support, or returns.",
            },
        ),
        "rating": Score(
            instructions="What star rating does this review imply?",
            criteria=["1 star", "2 stars", "3 stars", "4 stars", "5 stars"],
        ),
        "needs_escalation": Noul(
            instructions=(
                "Does this review need human follow-up? "
                "True for angry customers, safety issues, or legal threats."
            ),
        ),
        "is_suspicious": Noul(
            instructions="Does this review look fake, incentivized, or like spam?",
        ),
    }
