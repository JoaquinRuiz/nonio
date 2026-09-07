"""Combinación de señales y criterio de desacuerdo (R-009, FR-007, FR-009).

Cada señal se normaliza contra la distribución nula de su categoría en el corpus
—un percentil—, no contra su escala bruta: las escalas de Fast-DetectGPT y
Binoculars no son comparables entre sí ni entre perfiles, y combinarlas sin
normalizar sería mezclar unidades. Normalizar contra la nula es además lo que
permite que `measured_fpr` signifique algo (Artículo III).

**La lectura exige acuerdo.** Si las dos señales normalizadas caen a lados
opuestos de su umbral y ambas superan un margen mínimo, el resultado es
abstención por desacuerdo. Un promedio ponderado habría producido una lectura
intermedia y confiada a partir de dos señales que se contradicen, que es
exactamente el caso en que el Artículo II obliga a abstenerse.

El margen mínimo evita abstenerse por ruido cuando ambas señales están pegadas al
umbral: un desacuerdo trivial no es un desacuerdo.
"""

from __future__ import annotations

import math

from nonio.calibration.table import CalibrationTable
from nonio.schema.enums import AbstentionCause, CorpusCategory, Level
from nonio.schema.models import Abstention, Reading, Signal

__all__ = ["DISAGREEMENT_MARGIN", "normalize", "combine"]

# Distancia mínima al umbral para que una discrepancia cuente como desacuerdo.
DISAGREEMENT_MARGIN = 0.15


def normalize(raw_value: float, null_distribution: list[float]) -> float:
    """Percentil del valor dentro de la distribución nula de la categoría."""
    if not null_distribution or math.isnan(raw_value):
        return float("nan")
    below = sum(1 for v in null_distribution if v <= raw_value)
    return below / len(null_distribution)


def _level(normalized: float, threshold: float) -> Level:
    if normalized >= threshold:
        return Level.ALTO
    if normalized >= threshold * 0.75:
        return Level.MODERADO
    return Level.BAJO


def combine(
    signals: list[Signal],
    table: CalibrationTable,
    category: CorpusCategory,
    *,
    margin: float = DISAGREEMENT_MARGIN,
) -> Reading | Abstention:
    """Devuelve la lectura combinada, o abstención por desacuerdo.

    `category` es la categoría de corpus más parecida a la entrada; de ella salen
    el umbral y la tasa de falsos positivos que acompañan a la lectura (FR-009).
    """
    stats = table.per_category.get(category)
    if stats is None:
        return Abstention(
            cause=AbstentionCause.UNCALIBRATED_LANGUAGE,
            detail=f"No hay calibración para la categoría {category.value!r}.",
            signals=tuple(signals),
        )

    usable = [s for s in signals if not math.isnan(s.normalized_value)]
    if not usable:
        return Abstention(
            cause=AbstentionCause.UNCALIBRATED_LANGUAGE,
            detail="Ninguna señal produjo un valor utilizable sobre este texto.",
            signals=tuple(signals),
        )

    threshold = stats.threshold
    above = [s for s in usable if s.normalized_value >= threshold]
    below = [s for s in usable if s.normalized_value < threshold]

    if above and below:
        peor_arriba = min(s.normalized_value - threshold for s in above)
        peor_abajo = min(threshold - s.normalized_value for s in below)
        if peor_arriba >= margin and peor_abajo >= margin:
            detalle = ", ".join(
                f"{s.name}={s.normalized_value:.2f}" for s in sorted(usable, key=lambda x: x.name)
            )
            return Abstention(
                cause=AbstentionCause.SIGNAL_DISAGREEMENT,
                detail=(
                    f"Las señales apuntan en direcciones contrarias respecto al umbral "
                    f"{threshold:.2f} y ambas superan el margen de {margin:.2f}: {detalle}."
                ),
                signals=tuple(signals),
            )

    combinado = sum(s.normalized_value for s in usable) / len(usable)
    return Reading(
        level=_level(combinado, threshold),
        signals=tuple(signals),
        applied_threshold=threshold,
        measured_fpr=stats.fpr,
        fpr_category=category,
        fpr_reproducible=stats.reproducible,
    )
