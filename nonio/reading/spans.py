"""Tramos que más contribuyen a la lectura global (FR-005, Artículo IV).

El usuario debe poder abrir el texto y ver los mismos tramos que vio el
algoritmo, así que los offsets son sobre el texto **original**, no sobre el
medible: si se devolvieran sobre el texto ya limpio de código y citas, no
casarían con lo que el usuario tiene delante.
"""

from __future__ import annotations

import math

from nonio.schema.models import Span
from nonio.segmentation.blocks import TextBlock
from nonio.signals.engine import Measurement

__all__ = ["top_spans"]


def top_spans(
    blocks: list[TextBlock], measurement: Measurement, *, limit: int = 3
) -> tuple[Span, ...]:
    """Devuelve los bloques con mayor señal, con su contribución normalizada."""
    puntuados: list[tuple[TextBlock, float]] = []
    for block in blocks:
        agg = measurement.aggregate(block.start, block.end)
        vals = [v for v in agg.values() if not math.isnan(v)]
        if vals:
            puntuados.append((block, sum(vals) / len(vals)))

    if not puntuados:
        return ()

    valores = [v for _, v in puntuados]
    lo, hi = min(valores), max(valores)
    rango = hi - lo

    ordenados = sorted(puntuados, key=lambda p: p[1], reverse=True)[:limit]
    return tuple(
        Span(
            start=b.start,
            end=b.end,
            # Sin rango (un solo bloque, o todos iguales) la contribución no es
            # informativa; se declara 1.0 en vez de inventar una diferencia.
            contribution=round((v - lo) / rango, 4) if rango > 1e-12 else 1.0,
        )
        for b, v in ordenados
    )
