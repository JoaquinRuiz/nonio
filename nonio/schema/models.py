"""Modelos de la salida estructurada.

Los invariantes constitucionales viven en los tipos, no en la documentación:

- Artículo I: no existe ningún campo de autoría. No hay forma de leerlo porque no
  hay forma de escribirlo.
- Artículo II: `Abstention` es un resultado de primera clase y serializa con el
  token que el artículo nombra, `insufficient_evidence`. No lleva `level`: el
  campo no existe en el tipo.
- Artículo III: `applied_threshold`, `measured_fpr` y `fpr_category` son
  obligatorios en `Reading`. Construir una lectura sin ellos es un error de
  programación, no un campo opcional.
- Artículo IV: `AnalysisResult.blocks` no es opcional.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from nonio.schema.enums import AbstentionCause, CorpusCategory, DetectionMethod, ExcludedKind, Level

SCHEMA_VERSION = "1.0.0"
"""Semver propio, independiente de la versión del paquete (Artículo VI).

Añadir campo es MINOR; quitar campo o cambiar el significado de uno existente es
MAJOR; el resto es PATCH.
"""


class _Strict(BaseModel):
    """Base común: prohíbe campos extra.

    Es la primera línea de defensa del Artículo I: un `is_ai` añadido por
    descuido no se serializa en silencio, revienta en validación.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


class Span(_Strict):
    """Tramo del texto original."""

    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]
    contribution: Annotated[float, Field(ge=0.0, le=1.0)] | None = None


class ExcludedSpan(_Strict):
    """Tramo excluido del cálculo (FR-027)."""

    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]
    kind: ExcludedKind
    detection: DetectionMethod


class Signal(_Strict):
    """Una métrica individual, con su valor y su estado de validación (FR-003)."""

    name: str
    raw_value: float
    normalized_value: Annotated[float, Field(ge=0.0, le=1.0)]
    expected_range: tuple[float, float]
    validated_languages: tuple[str, ...]


class Reading(_Strict):
    """Resultado combinado con nivel.

    Artículo III: umbral, FP medida y categoría emparejada son obligatorios. No
    hay bandera ni ruta que permita emitir el nivel sin ellos.
    """

    type: Literal["reading"] = "reading"
    level: Level
    signals: tuple[Signal, ...]
    applied_threshold: float
    measured_fpr: Annotated[float, Field(ge=0.0, le=1.0)]
    fpr_category: CorpusCategory
    fpr_reproducible: bool
    top_spans: tuple[Span, ...] = ()


class Abstention(_Strict):
    """Resultado sin nivel, con causa (Artículo II). No es un error.

    Serializa como `"type": "insufficient_evidence"`, el token que nombra el
    Artículo II y que la spec usa en FR-007 y en el escenario 4. `Abstention` es
    el nombre de la clase en Python; el contrato serializado usa el token
    constitucional.
    """

    type: Literal["insufficient_evidence"] = "insufficient_evidence"
    cause: AbstentionCause
    detail: str
    signals: tuple[Signal, ...] | None = None
    observed: float | None = None
    required: float | None = None


Result = Annotated[Reading | Abstention, Field(discriminator="type")]


class Block(_Strict):
    """Unidad de segmentación sobre la que se mide y se reporta (FR-004)."""

    index: Annotated[int, Field(ge=0)]
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]
    token_count: Annotated[int, Field(ge=0)]
    result: Result


class DocumentInfo(_Strict):
    """El documento entregado, tras limpiar marcado."""

    source: str
    detected_language: str | None
    measurable_word_count: Annotated[int, Field(ge=0)]
    excluded_ratio: Annotated[float, Field(ge=0.0, le=1.0)]
    excluded_spans: tuple[ExcludedSpan, ...] = ()


class ProfileInfo(_Strict):
    """Qué recursos de medición produjeron la lectura.

    Los umbrales pertenecen al perfil y no se transfieren entre perfiles (R-003),
    por eso la salida declara cuál se usó.
    """

    id: str
    observer_model: str
    performer_model: str
    validated_languages: tuple[str, ...]
    calibration_corpus_version: str | None = None


class AnalysisResult(_Strict):
    """Raíz de la salida estructurada.

    `blocks` no es opcional: el Artículo IV rechaza el agregado sin desglose,
    incluso cuando el documento es homogéneo.
    """

    schema_version: str = SCHEMA_VERSION
    nonio_version: str
    profile: ProfileInfo
    document: DocumentInfo
    result: Result
    blocks: tuple[Block, ...]
