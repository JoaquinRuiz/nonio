"""Constructores de ejemplo para los tests de contrato."""

from __future__ import annotations

from nonio.schema.enums import AbstentionCause, CorpusCategory, Level
from nonio.schema.models import (
    Abstention,
    AnalysisResult,
    Block,
    DocumentInfo,
    ProfileInfo,
    Reading,
    Signal,
)

SIGNALS = (
    Signal(
        name="binoculars",
        raw_value=0.81,
        normalized_value=0.94,
        expected_range=(0.55, 1.10),
        validated_languages=("es",),
    ),
    Signal(
        name="fast_detect_gpt",
        raw_value=2.41,
        normalized_value=0.91,
        expected_range=(-1.0, 4.0),
        validated_languages=("es",),
    ),
)

PROFILE = ProfileInfo(
    id="qwen2.5-0.5b",
    observer_model="Qwen/Qwen2.5-0.5B@abc123",
    performer_model="Qwen/Qwen2.5-0.5B-Instruct@abc123",
    validated_languages=("es",),
    calibration_corpus_version="2026.09",
)


def reading(level: Level = Level.ALTO) -> Reading:
    return Reading(
        level=level,
        signals=SIGNALS,
        applied_threshold=0.72,
        measured_fpr=0.031,
        fpr_category=CorpusCategory.HUMANO_PRE2022,
        fpr_reproducible=True,
    )


def abstention(cause: AbstentionCause = AbstentionCause.INSUFFICIENT_LENGTH) -> Abstention:
    return Abstention(
        cause=cause,
        detail="El texto tiene 90 palabras; el mínimo calibrado es 300.",
        observed=90,
        required=300,
    )


def analysis(result=None) -> AnalysisResult:
    return AnalysisResult(
        nonio_version="0.1.0",
        profile=PROFILE,
        document=DocumentInfo(
            source="ensayo.md",
            detected_language="es",
            measurable_word_count=812,
            excluded_ratio=0.14,
        ),
        result=result if result is not None else reading(),
        blocks=(
            Block(index=0, start=0, end=612, token_count=180, result=reading(Level.BAJO)),
            Block(index=1, start=613, end=780, token_count=46, result=abstention()),
        ),
    )
