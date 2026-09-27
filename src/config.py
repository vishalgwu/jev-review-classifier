"""Project configuration. Secrets come from the environment, never from files."""
import os


def get_api_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError(
            "TYPESAFE_API_KEY is not set. Export it first:\n"
            '  export TYPESAFE_API_KEY="your_key_here"'
        )
    return key


JEV_MODEL = os.getenv("JEV_MODEL", "jev-latest")

# Confidence-gated routing thresholds (TypeSafe's recommended pattern:
# answer tells you *what*, confidence tells you *whether to act*).
CONFIDENCE_AUTO_ACT = 0.90   # act without human involvement
CONFIDENCE_REVIEW = 0.50     # act but flag / log; below this -> human review

# Vendor pricing (input tokens only; output is free)
COST_PER_MTOK_INPUT_USD = 0.042
