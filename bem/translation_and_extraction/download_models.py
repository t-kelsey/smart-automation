"""Download the translation models once, while online (ADR-0010, ADR-0011).

Run from bem/ before the event, then use HF_HUB_OFFLINE=1 for runs:
    python download_models.py
"""

from mt import MODEL_FOR_LANG


def main() -> None:
    from transformers import MarianMTModel, MarianTokenizer

    for lang, candidates in MODEL_FOR_LANG.items():
        for name in candidates:
            try:
                MarianTokenizer.from_pretrained(name)
                MarianMTModel.from_pretrained(name)
                print(f"{lang}: {name} ready")
                break
            except Exception as err:
                print(f"{lang}: {name} failed ({err})")
        else:
            print(f"{lang}: no model could be downloaded")


if __name__ == "__main__":
    main()
