"""Step 4 (optional): let Jev score the closed-set fields and flag low-confidence records.

Jev can only answer typed questions about a state (Choice / Score / Noul). It cannot extract
values from text, so it is used here as an independent second opinion on:
  * bohrart   (Choice over a fixed list)
  * bohrzweck (Choice over a fixed list)
  * lgrb_geprueft (Noul: "does the text state it was checked by LGRB?")

IMPORTANT: the exact request/response format of Jev was not documented in the sources I could
check (only that the SDK exports Choice, Noul, Score, TypeSafeClient and that the REST endpoint
is POST https://api.typesafe.ai/v1/systemone). `ask_jev` below is therefore a stub: fill it in
from https://docs.typesafe.ai/introduction/quickstart. Everything around it is ready.

Setup:  pip install typesafe-sdk   and   export TYPESAFE_API_KEY=...
"""
from __future__ import annotations

from .schema import Bohrung
from .validate import KNOWN_BOHRART, KNOWN_BOHRZWECK, Issue

MIN_CONFIDENCE = 0.80  # tune on a hand-labelled sample


def ask_jev(state: str, questions: list[dict]) -> list[dict]:
    """Send ONE state with several typed questions in one request.

    Expected return: one dict per question, e.g.
        {"answer": "Bohrung mit Ausbau", "confidence": 0.93}
    For a Noul question: {"answer": True/False, "confidence": <probability of the answer>}.
    Map the real SDK response onto this shape.
    """
    raise NotImplementedError(
        "Fill in with the typesafe-sdk call (TypeSafeClient + Choice/Noul) per the Jev docs."
    )


def jev_review(b: Bohrung, source_text: str) -> list[Issue]:
    questions = [
        {"type": "choice", "name": "bohrart", "options": sorted(KNOWN_BOHRART),
         "question": "What drilling type is stated for this borehole?"},
        {"type": "choice", "name": "bohrzweck", "options": sorted(KNOWN_BOHRZWECK),
         "question": "What is the stated purpose of this borehole?"},
        {"type": "noul", "name": "lgrb_geprueft",
         "question": "Does the text state that the borehole data was checked by the LGRB?"},
    ]
    results = ask_jev(source_text, questions)
    extracted = {"bohrart": b.bohrart, "bohrzweck": b.bohrzweck, "lgrb_geprueft": b.lgrb_geprueft}

    issues: list[Issue] = []
    for q, r in zip(questions, results):
        name = q["name"]
        if r["confidence"] < MIN_CONFIDENCE:
            issues.append(Issue("warning", name, f"Jev confidence {r['confidence']:.2f} below {MIN_CONFIDENCE}"))
        # extracted is None for lgrb_geprueft means "not stated"; only compare when Qwen gave a value
        if extracted[name] is not None and r["answer"] != extracted[name]:
            issues.append(Issue("warning", name, f"Qwen='{extracted[name]}' vs Jev='{r['answer']}'"))
    return issues
