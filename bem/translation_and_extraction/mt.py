"""Local machine translation for terms the glossary doesn't cover (ADR-0018, ADR-0019).

Uses open-source MarianMT models (Helsinki-NLP opus-mt-<src>-en) from Hugging Face.
Each model is downloaded once (download_models.py) and then loaded from the local cache.
Set HF_HUB_OFFLINE=1 at run time to make sure nothing is fetched from the internet.
"""

import logging
from typing import Protocol

log = logging.getLogger(__name__)

# Candidate models per source language, tried in order. Norwegian tries its own model first and
# falls back to Danish, the closest language, if that one isn't available.
MODEL_FOR_LANG: dict[str, list[str]] = {
    "es": ["Helsinki-NLP/opus-mt-es-en"],
    "da": ["Helsinki-NLP/opus-mt-da-en"],
    "no": ["Helsinki-NLP/opus-mt-no-en", "Helsinki-NLP/opus-mt-da-en"],
    "de": ["Helsinki-NLP/opus-mt-de-en"],
    "fr": ["Helsinki-NLP/opus-mt-fr-en"],
}


class Translator(Protocol):
    def translate(self, text: str, src: str) -> str | None:
        """Translate text from language src to English. Return None if that isn't possible."""


class NullTranslator:
    """No machine translation: the glossary is the only lookup."""

    def translate(self, text: str, src: str) -> str | None:
        return None


class MarianTranslator:
    """Lazy-loading MarianMT translator. Models load on first use and results are cached."""

    def __init__(self) -> None:
        self._models: dict[str, tuple | None] = {}
        self._results: dict[tuple[str, str], str | None] = {}

    def translate(self, text: str, src: str) -> str | None:
        if src == "en":
            return text
        key = (text, src)
        if key not in self._results:
            self._results[key] = self._run(text, src)
        return self._results[key]

    def _run(self, text: str, src: str) -> str | None:
        pair = self._model(src)
        if pair is None:
            return None
        tokenizer, model = pair

        import torch

        with torch.no_grad():
            batch = tokenizer([text], return_tensors="pt", padding=True)
            output = model.generate(**batch, max_new_tokens=32)
        return tokenizer.decode(output[0], skip_special_tokens=True)

    def _model(self, src: str) -> tuple | None:
        if src not in self._models:
            self._models[src] = None
            for name in MODEL_FOR_LANG.get(src, []):
                try:
                    from transformers import MarianMTModel, MarianTokenizer

                    self._models[src] = (
                        MarianTokenizer.from_pretrained(name),
                        MarianMTModel.from_pretrained(name),
                    )
                    break
                except Exception as err:  # not downloaded yet, or offline
                    log.warning("translation model %s unavailable (%s)", name, err)
            if self._models[src] is None:
                log.warning("no translation model available for %r; those terms stay unresolved", src)
        return self._models[src]
