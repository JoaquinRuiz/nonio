"""Enumeraciones del contrato de salida.

Artículo I: no existe aquí ninguna enumeración de autoría. `Level` describe la
intensidad de una señal estadística, nunca quién escribió el texto.
"""

from __future__ import annotations

from enum import StrEnum


class Level(StrEnum):
    """Banda ordinal de SEÑAL, no de autoría (Artículo I)."""

    BAJO = "bajo"
    MODERADO = "moderado"
    ALTO = "alto"


class AbstentionCause(StrEnum):
    """Causas de abstención (FR-007, FR-008, FR-028).

    `INSUFFICIENT_LENGTH` e `INSUFFICIENT_AFTER_EXCLUSION` son distintas a
    propósito: la primera dice que el documento es corto, la segunda que lo que
    quedó tras excluir código, tablas y citas lo es (FR-028).
    """

    INSUFFICIENT_LENGTH = "insufficient_length"
    INSUFFICIENT_AFTER_EXCLUSION = "insufficient_after_exclusion"
    UNCALIBRATED_LANGUAGE = "uncalibrated_language"
    SIGNAL_DISAGREEMENT = "signal_disagreement"


class ExcludedKind(StrEnum):
    """Tipos de tramo excluido del cálculo (FR-027)."""

    CODE_BLOCK = "code_block"
    INLINE_CODE = "inline_code"
    TABLE = "table"
    BLOCKQUOTE = "blockquote"
    FOOTNOTE = "footnote"
    FRONT_MATTER = "front_matter"


class DetectionMethod(StrEnum):
    """Cómo se detectó un tramo excluido.

    El usuario debe poder distinguir lo detectado con certeza sobre un AST de lo
    inferido por heurística (R-004).
    """

    AST = "ast"
    HEURISTIC = "heuristic"


class CorpusCategory(StrEnum):
    """Las cinco categorías que exige el Artículo VII."""

    HUMANO_PRE2022 = "humano_pre2022"
    GENERADO = "generado"
    MIXTO = "mixto"
    ESPANOL_NO_NATIVO = "espanol_no_nativo"
    TECNICA_ESTRUCTURADA = "tecnica_estructurada"
