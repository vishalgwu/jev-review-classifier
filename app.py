"""Streamlit demo: paste a review, see every attribute + confidence live."""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.client import classify_review, flatten  # noqa: E402
from src.router import route_review  # noqa: E402

st.set_page_config(page_title="Jev Review Classifier", layout="centered")
st.title("🛍️ Multi-Attribute Review Classifier")
st.caption("Powered by Jev (TypeSafe AI) — one review in, five typed judgments out, in a single call.")

review = st.text_area(
    "Paste a product review",
    "The headphones sound amazing and battery lasts forever. Shipping took 2 weeks though.",
    height=120,
)

if st.button("Classify", type="primary"):
    if not os.environ.get("TYPESAFE_API_KEY"):
        st.error("Set the TYPESAFE_API_KEY environment variable first.")
        st.stop()
    with st.spinner("Asking Jev…"):
        response, latency_ms = classify_review(review)
    flat = flatten(response)
    routing = route_review(flat)

    st.success(f"Done in {latency_ms:.0f} ms · model `{flat['model']}`")

    c1, c2, c3 = st.columns(3)
    c1.metric("Sentiment", flat["sentiment"], f"conf {flat['sentiment__confidence']:.2f}")
    c2.metric("Problem aspect", flat["aspect"], f"conf {flat['aspect__confidence']:.2f}")
    c3.metric("Implied rating", flat["rating__label"], f"conf {flat['rating__confidence']:.2f}")

    st.subheader("Confidence detail")
    for qid, label in (("sentiment", "Sentiment"), ("aspect", "Aspect"), ("rating", "Rating")):
        st.write(f"**{label}** — `{flat[qid]}`")
        probs = flat[qid + "__probs"]
        st.bar_chart({k: v for k, v in sorted(probs.items(), key=lambda x: -x[1])})

    c4, c5 = st.columns(2)
    c4.metric("Needs escalation", f"{flat['needs_escalation']:.0%}")
    c5.metric("Looks suspicious", f"{flat['is_suspicious']:.0%}")

    badge = {"auto_act": "🟢", "act_with_log": "🟡", "human_review": "🔴"}[routing["overall"]]
    st.subheader("Routing decision")
    st.write(f"{badge} **{routing['overall']}**")
    st.json(routing)
