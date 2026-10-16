"""Split translated markdown into one Borehole per borehole ID (ADR-0007).

Runs after OCR and translation. A line with a borehole label ("Borehole No.: T01",
"SONDEO Nº 7", a table cell after "Borehole No.") starts a new section. Lines after
it belong to that borehole until the next label. Lines before the first label go
to the first borehole.
"""

import re

from schema import Borehole

# Labels that introduce a borehole ID, e.g.
#   "HOLE NO : BH_AB05S", "Borehole No.:   T01", "Borehole No. ( 1 )",
#   "SONDEO Nº 7", "Bohrung B 3", "| Borehole No. | T01 |".
# Breakdown of the pattern:
#   (?:...)              the label word(s)
#   \s*(?:no|nr|n[º°o])?\.?   optional "No"/"Nr"/"Nº"/"N°", optional dot
#   [ \t:#(|]*           separators: spaces, ":", "#", "(", and "|" for markdown table cells
#   (?P<id>...)          the ID: a token of letters/digits/-/_, optionally followed by
#                        a second token after one space ("BH 2"). Dots are left out on
#                        purpose: headings like "BOREHOLE LOGS.-SKM04A" or dotted table
#                        of contents lines would otherwise be read as IDs.
# The regex alone is too permissive; _plausible_id() filters the candidates.
BOREHOLE_ID_RE = re.compile(
    r"\b(?:bore\s?hole|drill\s?hole|hole|bohrung|sondeo|sondagem|sondage|forage|boring|brønn)"
    r"\s*(?:no|nr|n[º°o])?\.?[ \t:#(|]*"
    r"(?P<id>[A-Z0-9][A-Z0-9_-]*(?: [A-Z0-9_-]+)?)",
    re.IGNORECASE,
)

# "DEPTH OF BOREHOLE 8.0m" / "End of borehole 8m" match the label too; a bare
# number with a length unit is a depth, not an ID. Two cases: "8m" is captured
# whole as the candidate, while for "8.0m" the ID regex stops at the dot, so the
# unit has to be looked for in the text right after the match.
DEPTH_RE = re.compile(r"\d+\s*(?:m|ft)", re.IGNORECASE)
DEPTH_AFTER_RE = re.compile(r"\s*(?:[.,]\d+)?\s*(?:m|ft)\b", re.IGNORECASE)


def find_borehole_id(line: str) -> str | None:
    """Return the normalised borehole ID named on this line, if there is one."""
    for match in BOREHOLE_ID_RE.finditer(line):
        candidate = match.group("id").strip(" -_")
        if DEPTH_RE.fullmatch(candidate) or DEPTH_AFTER_RE.match(line, match.end()):
            continue
        if _plausible_id(candidate):
            return _normalise_id(candidate)
    return None


def split(source_file: str, markdown: str) -> list[Borehole]:
    """Group the markdown lines into one Borehole per borehole ID."""
    lines = markdown.splitlines()
    # Matching one line at a time keeps each ID tied to its own row. A label in one
    # line can't pick up an ID from a different row or table cell.
    found = [find_borehole_id(line) for line in lines]

    current: str | None = next((i for i in found if i), None)
    sections: dict[str | None, list[str]] = {}
    for line, bid in zip(lines, found):
        current = bid or current
        sections.setdefault(current, []).append(line)

    return [
        Borehole(source_file=source_file, borehole_id=bid, raw_markdown="\n".join(section))
        for bid, section in sections.items()
    ]


def _plausible_id(candidate: str) -> bool:
    """Reject regex matches that are words, not IDs ("Borehole Log", "hole diameter").

    Accepted: the first token has a digit ("T01", "BH_AB05S", "1"), or it's a
    short prefix followed by a numbered token ("BH 2"). Otherwise the label was
    followed by an ordinary word and a second token that happens to contain a
    digit ("Borehole Details 5") would slip through.
    """
    first, _, second = candidate.partition(" ")
    if any(c.isdigit() for c in first):
        return True
    return first.isalpha() and len(first) <= 4 and any(c.isdigit() for c in second)


def _normalise_id(raw: str) -> str:
    # "bh 2", "BH-2" and "BH_2" should all end up as the same borehole.
    return re.sub(r"[\s_-]+", "-", raw.strip()).upper()
