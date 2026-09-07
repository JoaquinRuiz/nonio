"""Exclusión sobre HTML (FR-027).

lxml da offsets de línea pero no de carácter, así que se localiza cada elemento
excluible por su literal en el origen. Es exacto para los casos que importan
—`<pre>`, `<code>`, `<table>`, `<blockquote>`— y se marca como AST porque la
identificación del elemento sí viene del parser.
"""

from __future__ import annotations

import re

from nonio.schema.enums import DetectionMethod, ExcludedKind
from nonio.schema.models import ExcludedSpan

_TAGS: dict[str, ExcludedKind] = {
    "pre": ExcludedKind.CODE_BLOCK,
    "code": ExcludedKind.INLINE_CODE,
    "table": ExcludedKind.TABLE,
    "blockquote": ExcludedKind.BLOCKQUOTE,
}


def find_excluded_spans(text: str) -> list[ExcludedSpan]:
    spans: list[ExcludedSpan] = []
    for tag, kind in _TAGS.items():
        pattern = re.compile(rf"<{tag}\b[^>]*>.*?</{tag}>", re.DOTALL | re.IGNORECASE)
        for m in pattern.finditer(text):
            spans.append(
                ExcludedSpan(start=m.start(), end=m.end(), kind=kind, detection=DetectionMethod.AST)
            )
    return spans


def strip_tags(text: str) -> str:
    """Quita el marcado restante para que no cuente como texto (caso límite de la spec)."""
    return re.sub(r"<[^>]+>", " ", text)
