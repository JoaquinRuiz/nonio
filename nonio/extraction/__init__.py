"""Extracción del texto medible y de los tramos excluidos (FR-027).

Las cifras de calibración publicadas se miden sobre el texto ya excluido, no
sobre el documento bruto: quien compare un `excluded_ratio` alto con una lectura
debe saber que la lectura se hizo sobre lo que quedó.
"""

from __future__ import annotations

from dataclasses import dataclass

from nonio.extraction import html as _html
from nonio.extraction import markdown as _markdown
from nonio.extraction import plaintext as _plaintext
from nonio.schema.models import ExcludedSpan

__all__ = ["Extraction", "extract"]


@dataclass(frozen=True)
class Extraction:
    """Resultado de la extracción.

    `measurable_text` conserva la longitud del original: los tramos excluidos se
    sustituyen por espacios en vez de eliminarse, de modo que todo offset sigue
    apuntando al texto original (FR-005).
    """

    raw_text: str
    measurable_text: str
    excluded_spans: tuple[ExcludedSpan, ...]
    excluded_ratio: float

    @property
    def measurable_word_count(self) -> int:
        return len(self.measurable_text.split())


def _merge(spans: list[ExcludedSpan]) -> list[ExcludedSpan]:
    """Funde solapamientos conservando el tipo del tramo más externo."""
    if not spans:
        return []
    ordered = sorted(spans, key=lambda s: (s.start, -s.end))
    merged = [ordered[0]]
    for s in ordered[1:]:
        last = merged[-1]
        if s.start < last.end:
            if s.end > last.end:
                merged[-1] = ExcludedSpan(
                    start=last.start, end=s.end, kind=last.kind, detection=last.detection
                )
        else:
            merged.append(s)
    return merged


def _looks_like_html(text: str) -> bool:
    lowered = text[:4096].lower()
    return any(t in lowered for t in ("<html", "<body", "<div", "<p>", "<pre", "<table"))


def extract(text: str) -> Extraction:
    """Devuelve el texto medible, los tramos excluidos y la proporción excluida."""
    spans: list[ExcludedSpan] = []
    if _looks_like_html(text):
        spans += _html.find_excluded_spans(text)
    spans += _markdown.find_excluded_spans(text)
    spans += _plaintext.find_excluded_spans(text)

    merged = _merge(spans)

    chars = list(text)
    for s in merged:
        for i in range(s.start, min(s.end, len(chars))):
            if chars[i] != "\n":
                chars[i] = " "
    measurable = "".join(chars)

    excluded_chars = sum(s.end - s.start for s in merged)
    ratio = (excluded_chars / len(text)) if text else 0.0

    return Extraction(
        raw_text=text,
        measurable_text=measurable,
        excluded_spans=tuple(merged),
        excluded_ratio=min(1.0, max(0.0, ratio)),
    )
