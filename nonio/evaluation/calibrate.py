"""Calibración: umbrales y tasas de error por categoría (T032, FR-009, FR-021).

Mide las señales sobre el corpus, elige el umbral y calcula, **por categoría**,
la tasa de aciertos y la de falsos positivos. Nunca produce una cifra agregada:
el Artículo III prohíbe publicar precisión global sin desglose porque la media
esconde justo el daño de este dominio.

El mínimo de longitud NO se fija por criterio sino midiendo dónde la señal supera
el ruido, y se reporta el sesgo de selección que introduce: subir el mínimo
descarta preferentemente los textos más cortos, que en la categoría de no nativo
correlacionan con menor dominio del idioma. Elegir un mínimo alto mejoraría las
cifras escondiendo a quien más riesgo corre — lo contrario de lo que pide el
Artículo III.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from pathlib import Path

from nonio.backends.loader import LoadedPair
from nonio.calibration.corpus import CorpusCase
from nonio.calibration.table import CalibrationTable, CategoryStats
from nonio.schema.enums import CorpusCategory
from nonio.signals.engine import measure

__all__ = ["CaseMeasurement", "measure_cases", "fit_table", "selection_bias", "bias_ci"]

# Categorías cuya presencia de señal se considera "positiva" al calibrar.
POSITIVE = {CorpusCategory.GENERADO}


@dataclass(frozen=True)
class CaseMeasurement:
    case_id: str
    category: CorpusCategory
    word_count: int
    signals: dict[str, float]


def measure_cases(
    cases: list[CorpusCase],
    root: Path,
    pair: LoadedPair,
    *,
    limit_per_category: int | None = None,
    progress: bool = True,
) -> list[CaseMeasurement]:
    """Mide el corpus. Informa de progreso: medir miles de textos tarda una hora
    y un proceso opaco durante una hora es un proceso que nadie sabe si colgó."""
    import sys
    import time
    from collections import Counter

    por_categoria: dict[CorpusCategory, int] = {}
    out: list[CaseMeasurement] = []
    omitidos: list[tuple[str, str]] = []

    # El objetivo NO es len(cases): con un tope por categoría, la mayoría de los
    # casos se saltan sin medirse. Estimar sobre el total sobreestima el tiempo
    # restante varias veces —lo hacía 5x— y un ETA que miente es peor que
    # ninguno, que es la razón por la que existe este indicador.
    disponibles = Counter(c.category for c in cases)
    objetivo = (
        sum(min(limit_per_category, n) for n in disponibles.values())
        if limit_per_category is not None
        else len(cases)
    )
    t0 = time.time()
    _ultimo = -1
    for case in cases:
        if progress and out and len(out) % 50 == 0 and _ultimo != len(out):
            _ultimo = len(out)
            hechos = len(out)
            ritmo = (time.time() - t0) / max(1, hechos)
            print(
                f"  {hechos}/{objetivo} medidos  {ritmo:.1f}s/texto  "
                f"ETA {ritmo * max(0, objetivo - hechos) / 60:.0f} min",
                file=sys.stderr,
                flush=True,
            )
        n = por_categoria.get(case.category, 0)
        if limit_per_category is not None and n >= limit_per_category:
            continue
        try:
            text = case.read_text(root)
        except OSError as exc:
            # Una fila mala no puede tirar una hora de cómputo. Se cuenta y se
            # reporta al final: perder un caso es aceptable, perder la medición no.
            omitidos.append((case.id, str(exc)))
            continue
        m = measure(text, pair)
        agg = m.aggregate(0, len(text))
        if any(math.isnan(v) for v in agg.values()):
            continue
        por_categoria[case.category] = n + 1
        out.append(
            CaseMeasurement(
                case_id=case.id,
                category=case.category,
                word_count=len(text.split()),
                signals=agg,
            )
        )
    if omitidos and progress:
        print(
            f"  aviso: {len(omitidos)} casos omitidos por error de lectura "
            f"(p. ej. {omitidos[0][0]})",
            file=sys.stderr,
        )
    return out


def _combined(m: CaseMeasurement, nulls: dict[str, list[float]]) -> float:
    """Percentil medio de las señales contra la nula de referencia (R-009)."""
    vals = []
    for name, raw in m.signals.items():
        null = nulls.get(name) or []
        if not null:
            continue
        vals.append(sum(1 for v in null if v <= raw) / len(null))
    return sum(vals) / len(vals) if vals else float("nan")


def selection_bias(
    measurements: list[CaseMeasurement], category: CorpusCategory, min_words: int
) -> dict[str, float]:
    """Cuánto descarta un mínimo dado, y hacia dónde sesga."""
    cat = [m for m in measurements if m.category is category]
    if not cat:
        return {}
    retenidos = [m for m in cat if m.word_count >= min_words]
    return {
        "total": len(cat),
        "retenidos": len(retenidos),
        "proporcion_retenida": len(retenidos) / len(cat),
        "mediana_todos": statistics.median(m.word_count for m in cat),
        "mediana_retenidos": (
            statistics.median(m.word_count for m in retenidos) if retenidos else float("nan")
        ),
    }


def fit_table(
    measurements: list[CaseMeasurement],
    *,
    profile_id: str,
    language: str,
    corpus_version: str,
    min_words: int,
    target_fpr: float = 0.05,
    reproducible: dict[str, bool] | None = None,
) -> CalibrationTable:
    """Ajusta umbral y calcula TPR/FPR por categoría.

    El umbral se elige sobre la categoría de referencia humana para dar la tasa
    de falsos positivos objetivo, y luego se **mide** qué produce ese mismo
    umbral en cada una de las demás. Elegir un umbral distinto por categoría
    haría las cifras incomparables y escondería el sesgo.
    """
    usables = [m for m in measurements if m.word_count >= min_words]
    nulls: dict[str, list[float]] = {}
    referencia = [m for m in usables if m.category is CorpusCategory.HUMANO_PRE2022]
    for name in (measurements[0].signals if measurements else {}):
        nulls[name] = sorted(m.signals[name] for m in referencia)

    if not referencia:
        raise ValueError("Sin categoría humano_pre2022 no hay nula contra la que normalizar")

    ref_scores = sorted(_combined(m, nulls) for m in referencia)
    idx = max(0, min(len(ref_scores) - 1, int(round((1 - target_fpr) * (len(ref_scores) - 1)))))
    threshold = ref_scores[idx]

    per_category: dict[CorpusCategory, CategoryStats] = {}
    for category in CorpusCategory:
        grupo = [m for m in usables if m.category is category]
        if not grupo:
            continue
        scores = [_combined(m, nulls) for m in grupo]
        por_encima = sum(1 for s in scores if s >= threshold)
        rate = por_encima / len(grupo)
        es_positiva = category in POSITIVE
        per_category[category] = CategoryStats(
            threshold=round(threshold, 6),
            tpr=round(rate if es_positiva else 0.0, 6),
            fpr=round(0.0 if es_positiva else rate, 6),
            n_samples=len(grupo),
            # FR-029 / SC-003: una cifra del corpus privado no la puede
            # reproducir un tercero, y debe viajar diciéndolo.
            reproducible=(reproducible or {}).get(category.value, True),
        )

    return CalibrationTable(
        profile_id=profile_id,
        language=language,
        min_words=min_words,
        corpus_version=corpus_version,
        per_category=per_category,
    )


def bias_ci(
    measurements: list[CaseMeasurement],
    *,
    threshold: float,
    min_words: int,
    resamples: int = 4000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Intervalo de confianza del cociente de sesgo por bootstrap (FR-031).

    Se calcula aquí y no en un script suelto porque FR-031 prohíbe publicar una
    cifra de sesgo sin su intervalo: si calcularlo dependiera de que alguien se
    acuerde, tarde o temprano no se acordaría. Devuelve (mediana, p2.5, p97.5).
    """
    import random

    usables = [m for m in measurements if m.word_count >= min_words]
    ref = [m for m in usables if m.category is CorpusCategory.HUMANO_PRE2022]
    nn = [m for m in usables if m.category is CorpusCategory.ESPANOL_NO_NATIVO]
    if not ref or not nn:
        return (float("nan"), float("nan"), float("nan"))

    nulls = {name: sorted(m.signals[name] for m in ref) for name in usables[0].signals}
    scores = {m.case_id: _combined(m, nulls) for m in usables}

    rng = random.Random(seed)
    ratios: list[float] = []
    for _ in range(resamples):
        a = rng.choices(ref, k=len(ref))
        b = rng.choices(nn, k=len(nn))
        fa = sum(1 for m in a if scores[m.case_id] >= threshold) / len(a)
        fb = sum(1 for m in b if scores[m.case_id] >= threshold) / len(b)
        if fa > 0:
            ratios.append(fb / fa)
    if not ratios:
        return (float("nan"), float("nan"), float("nan"))
    ratios.sort()
    return (
        statistics.median(ratios),
        ratios[int(0.025 * len(ratios))],
        ratios[int(0.975 * len(ratios))],
    )
