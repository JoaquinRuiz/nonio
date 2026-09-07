"""Heurística de citas en texto plano (FR-027, R-004).

Sin marcado no hay AST, así que esto es inferencia y se marca como tal
(`detection="heuristic"`). La documentación declara qué detecta y qué no
(FR-025), y el porcentaje excluido reportado permite al usuario ver que la
exclusión fue parcial.
"""

from __future__ import annotations

import re

from nonio.schema.enums import DetectionMethod, ExcludedKind
from nonio.schema.models import ExcludedSpan

# Líneas que empiezan por '>' — convención de cita heredada del correo.
_QUOTE_LINE = re.compile(r"^[ \t]*>.*$", re.MULTILINE)
# Bloques largos entre comillas tipográficas o rectas (>= 120 caracteres).
_LONG_QUOTE = re.compile(r"[«“\"]([^«»“”\"]{120,})[»”\"]")


def find_excluded_spans(text: str) -> list[ExcludedSpan]:
    spans: list[ExcludedSpan] = []
    for m in _QUOTE_LINE.finditer(text):
        spans.append(
            ExcludedSpan(
                start=m.start(),
                end=m.end(),
                kind=ExcludedKind.BLOCKQUOTE,
                detection=DetectionMethod.HEURISTIC,
            )
        )
    for m in _LONG_QUOTE.finditer(text):
        spans.append(
            ExcludedSpan(
                start=m.start(),
                end=m.end(),
                kind=ExcludedKind.BLOCKQUOTE,
                detection=DetectionMethod.HEURISTIC,
            )
        )
    return spans
