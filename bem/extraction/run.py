from dataclasses import asdict

from .extract import extract, make_client
from .render import render
from .validate import check_all, status


def run_extraction(text: str, model: str, base_url: str = "http://localhost:11434/v1") -> dict:
    b = extract(text, make_client(base_url), model)
    b.schichten.sort(key=lambda l: l.von_m)
    issues = check_all(b, text)
    return {
        "record": b.model_dump(mode="json"),
        "markdown": render(b),
        "status": status(issues),
        "issues": [asdict(i) for i in issues],
    }
