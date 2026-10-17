"""Translate the fake OCR markdown under output/fake_ocr and write the results to output/translate."""

from pathlib import Path

from translation_and_extraction import translate

BEM_DIR = Path(__file__).resolve().parents[1]
FAKE_OCR_DIR = BEM_DIR / "output" / "fake_ocr"
TRANSLATE_DIR = BEM_DIR / "output" / "translate"

TRANSLATE_DIR.mkdir(parents=True, exist_ok=True)
for path in sorted(FAKE_OCR_DIR.glob("*.md")):
    translated, errors = translate(path.read_text(encoding="utf-8"))
    out_path = TRANSLATE_DIR / path.name
    out_path.write_text(translated, encoding="utf-8")
    print(f"{path.name}: {len(errors)} translate_error(s) -> {out_path.relative_to(BEM_DIR)}")
    for error in errors:
        print(f"  {error}")
