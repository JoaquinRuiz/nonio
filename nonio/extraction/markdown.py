"""Exclusión de código, tablas y citas sobre el AST de Markdown (FR-027, R-004).

Se usa un parser real y no expresiones regulares porque FR-027 exige reportar el
porcentaje excluido, y eso obliga a conocer con exactitud dónde empieza y acaba
cada tramo. Un offset erróneo además rompería FR-005, que señala los tramos
contribuyentes sobre el texto original.
"""

from __future__ import annotations

from markdown_it import MarkdownIt

from nonio.schema.enums import DetectionMethod, ExcludedKind
from nonio.schema.models import ExcludedSpan

_TOKEN_KINDS: dict[str, ExcludedKind] = {
    "fence": ExcludedKind.CODE_BLOCK,
    "code_block": ExcludedKind.CODE_BLOCK,
    "table_open": ExcludedKind.TABLE,
    "blockquote_open": ExcludedKind.BLOCKQUOTE,
    "footnote_block_open": ExcludedKind.FOOTNOTE,
}

_md = MarkdownIt("commonmark").enable("table")


def _line_offsets(text: str) -> list[int]:
    """Offset de carácter donde empieza cada línea."""
    offsets, pos = [0], 0
    for line in text.splitlines(keepends=True):
        pos += len(line)
        offsets.append(pos)
    return offsets


def find_excluded_spans(text: str) -> list[ExcludedSpan]:
    """Devuelve los tramos de Markdown que no deben medirse.

    Cubre bloques de código cercados e indentados, tablas, citas en bloque, notas
    al pie, front matter y código en línea.
    """
    spans: list[ExcludedSpan] = []
    lines = _line_offsets(text)

    def span_of(token, kind: ExcludedKind) -> ExcludedSpan | None:
        if not token.map:
            return None
        first, last = token.map
        start = lines[min(first, len(lines) - 1)]
        end = lines[min(last, len(lines) - 1)]
        return ExcludedSpan(start=start, end=end, kind=kind, detection=DetectionMethod.AST)

    tokens = _md.parse(text)
    depth_stack: list[tuple[str, int]] = []

    for token in tokens:
        if token.type == "front_matter":
            s = span_of(token, ExcludedKind.FRONT_MATTER)
            if s:
                spans.append(s)
        elif token.type in ("fence", "code_block"):
            s = span_of(token, ExcludedKind.CODE_BLOCK)
            if s:
                spans.append(s)
        elif token.type in ("table_open", "blockquote_open", "footnote_block_open"):
            depth_stack.append((token.type, len(spans)))
            s = span_of(token, _TOKEN_KINDS[token.type])
            if s:
                spans.append(s)
        elif token.type == "inline" and token.children:
            for child in token.children:
                # El AST no da offsets de inline; se localiza el literal en la línea.
                if child.type == "code_inline" and token.map:
                    lo = lines[token.map[0]]
                    hi = lines[min(token.map[1], len(lines) - 1)]
                    idx = text.find(child.content, lo, hi)
                    if idx != -1:
                        spans.append(
                            ExcludedSpan(
                                start=idx,
                                end=idx + len(child.content),
                                kind=ExcludedKind.INLINE_CODE,
                                detection=DetectionMethod.AST,
                            )
                        )
    return spans
