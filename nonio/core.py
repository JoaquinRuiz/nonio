"""Orquestación del análisis (FR-011, FR-012, escenarios 1-9).

    texto bruto
      -> extracción      excluye código, tablas, citas; registra % excluido  FR-027
      -> idioma          si no hay calibración -> abstención                 FR-007
      -> segmentación    bloques con mínimo de tokens                        FR-004
      -> longitud        si el medible < mínimo -> abstención por exclusión  FR-028
      -> una pasada por modelo, acumulando por bloque                        R-007
      -> señales por bloque y documento                                      FR-003
      -> combinación     si discrepan -> abstención                          FR-007
      -> lectura con umbral + FP de categoría + tramos                       FR-009, FR-005

**La abstención nunca viaja como excepción.** Va en `result.result` como
`Abstention`, porque el Artículo II la declara resultado de primera clase y
lanzar una excepción la convertiría en fallo. Las excepciones quedan reservadas a
condiciones de entorno: falta un modelo, la entrada no se puede leer.
"""

from __future__ import annotations

import math
from pathlib import Path

from nonio.backends.loader import LoadedPair, load_pair
from nonio.calibration.table import CalibrationTable
from nonio.extraction import extract
from nonio.language.detect import detect_language
from nonio.reading.category import match_category
from nonio.reading.combine import combine, normalize
from nonio.reading.spans import top_spans
from nonio.schema.enums import AbstentionCause, Level
from nonio.schema.models import (
    SCHEMA_VERSION,
    Abstention,
    AnalysisResult,
    Block,
    DocumentInfo,
    ProfileInfo,
    Reading,
    Signal,
)
from nonio.segmentation.blocks import segment
from nonio.signals.engine import SCORERS, measure

__all__ = ["analyze", "UnreadableInputError"]

NONIO_VERSION = "0.1.0"
MIN_BLOCK_TOKENS = 120


class UnreadableInputError(RuntimeError):
    """La entrada no se puede leer o decodificar. Condición de entorno."""


def _profile_info(pair: LoadedPair, table: CalibrationTable | None) -> ProfileInfo:
    p = pair.profile
    return ProfileInfo(
        id=p.id,
        observer_model=f"{p.observer_model}@{p.revision}",
        performer_model=f"{p.performer_model}@{p.revision}",
        validated_languages=p.validated_languages,
        calibration_corpus_version=table.corpus_version if table else None,
    )


def _read_input(text: str | Path) -> tuple[str, str]:
    if isinstance(text, Path):
        try:
            return text.read_text(encoding="utf-8"), str(text)
        except (OSError, UnicodeDecodeError) as exc:
            raise UnreadableInputError(f"No se pudo leer {text}: {exc}") from exc
    return text, "<stdin>"


def _abstain(
    cause: AbstentionCause,
    detail: str,
    *,
    profile: ProfileInfo,
    document: DocumentInfo,
    observed: float | None = None,
    required: float | None = None,
    signals: tuple[Signal, ...] | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        schema_version=SCHEMA_VERSION,
        nonio_version=NONIO_VERSION,
        profile=profile,
        document=document,
        result=Abstention(
            cause=cause, detail=detail, observed=observed, required=required, signals=signals
        ),
        blocks=(),
    )


def analyze(
    text: str | Path,
    *,
    profile: str | None = None,
    language: str | None = None,
    min_words: int | None = None,
    table: CalibrationTable | None = None,
) -> AnalysisResult:
    """Analiza un texto y devuelve una lectura o una abstención con causa."""
    raw, source = _read_input(text)
    pair = load_pair(profile)

    extraction = extract(raw)
    # Forzar el idioma no autoriza a extrapolar umbrales de otro (Artículo VIII):
    # se usa el declarado, pero si no hay calibración para él, se abstiene igual.
    detected = language or detect_language(extraction.measurable_text)

    document = DocumentInfo(
        source=source,
        detected_language=detected,
        measurable_word_count=extraction.measurable_word_count,
        excluded_ratio=round(extraction.excluded_ratio, 4),
        excluded_spans=extraction.excluded_spans,
    )
    profile_info = _profile_info(pair, table)

    if table is None:
        return _abstain(
            AbstentionCause.UNCALIBRATED_LANGUAGE,
            "No hay tabla de calibración disponible. Nonio no publica una lectura sin la "
            "tasa de falsos positivos medida de su umbral (Artículo III).",
            profile=profile_info,
            document=document,
        )
    if detected is None or detected != table.language:
        return _abstain(
            AbstentionCause.UNCALIBRATED_LANGUAGE,
            f"No hay calibración para el idioma {detected!r}; la disponible es "
            f"{table.language!r}. Extrapolar umbrales entre idiomas está prohibido.",
            profile=profile_info,
            document=document,
        )

    minimo = min_words if min_words is not None else table.min_words
    if extraction.measurable_word_count < minimo:
        # FR-028: distinguir "el documento es corto" de "lo que quedó tras excluir lo es".
        bruto = len(raw.split())
        por_exclusion = bruto >= minimo
        return _abstain(
            (
                AbstentionCause.INSUFFICIENT_AFTER_EXCLUSION
                if por_exclusion
                else AbstentionCause.INSUFFICIENT_LENGTH
            ),
            (
                f"Tras excluir código, tablas y citas quedan {extraction.measurable_word_count} "
                f"palabras medibles de {bruto}; el mínimo calibrado es {minimo}."
                if por_exclusion
                else f"El texto tiene {extraction.measurable_word_count} palabras; "
                f"el mínimo calibrado es {minimo}."
            ),
            profile=profile_info,
            document=document,
            observed=extraction.measurable_word_count,
            required=minimo,
        )

    measurement = measure(extraction.measurable_text, pair)
    category = match_category(raw, excluded_ratio=extraction.excluded_ratio)
    nulls = getattr(table, "_nulls", {}) or {}

    def _signals(start: int, end: int) -> list[Signal]:
        agg = measurement.aggregate(start, end)
        out = []
        for scorer in SCORERS:
            raw_value = agg.get(scorer.name, float("nan"))
            out.append(
                Signal(
                    name=scorer.name,
                    raw_value=(0.0 if math.isnan(raw_value) else round(raw_value, 6)),
                    normalized_value=normalize(raw_value, nulls.get(scorer.name, [])),
                    expected_range=scorer.expected_range,
                    validated_languages=pair.profile.validated_languages,
                )
            )
        return out

    blocks_text = segment(extraction.measurable_text, min_words=40)
    blocks: list[Block] = []
    for tb in blocks_text:
        lo, hi = measurement.token_range(tb.start, tb.end)
        n_tok = max(0, hi - lo)
        if n_tok < MIN_BLOCK_TOKENS:
            # Un bloque corto no recibe lectura de baja confianza: se abstiene.
            resultado: Reading | Abstention = Abstention(
                cause=AbstentionCause.INSUFFICIENT_LENGTH,
                detail=f"El bloque tiene {n_tok} tokens; el mínimo es {MIN_BLOCK_TOKENS}.",
                observed=n_tok,
                required=MIN_BLOCK_TOKENS,
            )
        else:
            resultado = combine(_signals(tb.start, tb.end), table, category)
        blocks.append(
            Block(index=tb.index, start=tb.start, end=tb.end, token_count=n_tok, result=resultado)
        )

    doc_signals = _signals(0, len(extraction.measurable_text))
    doc_result = combine(doc_signals, table, category)
    if isinstance(doc_result, Reading):
        doc_result = doc_result.model_copy(
            update={"top_spans": top_spans(blocks_text, measurement)}
        )

    return AnalysisResult(
        schema_version=SCHEMA_VERSION,
        nonio_version=NONIO_VERSION,
        profile=profile_info,
        document=document,
        result=doc_result,
        blocks=tuple(blocks),
    )


__all__ += ["Level"]
