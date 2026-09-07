"""Segmentación en bloques (FR-004).

Un bloque por debajo del mínimo de tokens no recibe lectura: recibe abstención
por longitud. Nunca una lectura de baja confianza — el Artículo II prefiere
abstenerse a arriesgar una medida que no se sostiene.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["TextBlock", "segment"]

_PARAGRAPH = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class TextBlock:
    index: int
    start: int
    end: int
    text: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def segment(text: str, *, min_words: int = 40) -> list[TextBlock]:
    """Divide por párrafos y funde los que no alcanzan `min_words`.

    Fundir en vez de descartar evita que un documento de párrafos cortos se
    quede sin bloques medibles por pura tipografía.
    """
    if not text.strip():
        return []

    raw: list[tuple[int, int]] = []
    pos = 0
    for part in _PARAGRAPH.split(text):
        idx = text.find(part, pos)
        if idx == -1:
            continue
        if part.strip():
            raw.append((idx, idx + len(part)))
        pos = idx + len(part)

    if not raw:
        return []

    merged: list[tuple[int, int]] = []
    for start, end in raw:
        if merged and len(text[merged[-1][0] : merged[-1][1]].split()) < min_words:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))

    return [TextBlock(index=i, start=s, end=e, text=text[s:e]) for i, (s, e) in enumerate(merged)]
