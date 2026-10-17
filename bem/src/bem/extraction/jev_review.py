"""Step 4 (optional): let Jev score the closed-set fields and flag low-confidence records.

Jev can only answer typed questions about a state (Choice / Score / Noul). It cannot extract
values from text, so it is used here as an independent second opinion on:
  * drilling_method (Choice over a fixed list)
  * purpose         (Choice over a fixed list)
A question is only asked once the matching KNOWN_* set in validate.py is filled.

IMPORTANT: the exact request/response format of Jev was not documented in the sources I could
check (only that the SDK exports Choice, Noul, Score, TypeSafeClient and that the REST endpoint
is POST https://api.typesafe.ai/v1/systemone). `ask_jev` below is therefore a stub: fill it in
from https://docs.typesafe.ai/introduction/quickstart. Everything around it is ready.

Setup:  pip install typesafe-sdk   and   export TYPESAFE_API_KEY=...
"""
from __future__ import annotations

from .schema import Borehole
from .validate import KNOWN_DRILLING_METHODS, KNOWN_PURPOSES, Issue

MIN_CONFIDENCE = 0.80  # tune on a hand-labelled sample


def ask_jev(state: str, questions: list[dict]) -> list[dict]:
    """Send ONE state with several typed questions in one request.

    Expected return: one dict per question, e.g.
        {"answer": "Rotary core", "confidence": 0.93}
    For a Noul question: {"answer": True/False, "confidence": <probability of the answer>}.
    Map the real SDK response onto this shape.
    """
    raise NotImplementedError(
        "Fill in with the typesafe-sdk call (TypeSafeClient + Choice/Noul) per the Jev docs."
    )


def jev_review(b: Borehole, source_text: str) -> list[Issue]:
    extracted = {"drilling_method": b.drilling_method, "purpose": b.purpose}
    questions = [
        {"type": "choice", "name": "drilling_method", "options": sorted(KNOWN_DRILLING_METHODS),
         "question": "What drilling method is stated for this borehole?"},
        {"type": "choice", "name": "purpose", "options": sorted(KNOWN_PURPOSES),
         "question": "What is the stated purpose of this borehole?"},
    ]
    questions = [q for q in questions if q["options"]]
    if not questions:
        return []
    results = ask_jev(source_text, questions)

    issues: list[Issue] = []
    for q, r in zip(questions, results):
        name = q["name"]
        if r["confidence"] < MIN_CONFIDENCE:
            issues.append(Issue("warning", name, f"Jev confidence {r['confidence']:.2f} below {MIN_CONFIDENCE}"))
        if extracted[name] is not None and r["answer"] != extracted[name]:
            issues.append(Issue("warning", name, f"Qwen='{extracted[name]}' vs Jev='{r['answer']}'"))
    return issues
