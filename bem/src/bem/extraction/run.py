from dataclasses import asdict

from .extract import extract, make_client
from .render import render
from .validate import check_all, status


def run_extraction(text: str, model: str | None = None, base_url: str | None = None) -> dict:
    b = extract(text, make_client(base_url), model)
    b.layers.sort(key=lambda l: l.depth_from_m)
    issues = check_all(b, text)
    return {
        "record": b.to_api_dict(),
        "markdown": render(b),
        "status": status(issues),
        "issues": [asdict(i) for i in issues],
    }
