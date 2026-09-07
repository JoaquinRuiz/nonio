"""Tabla de calibración por perfil (FR-009, FR-021, FR-030, R-003).

**Los umbrales pertenecen al perfil.** Aplicar los de `qwen2.5-0.5b` a
`salamandra-2b` es el mismo error que el Artículo VIII prohíbe entre idiomas, y
el cargador lo rechaza en vez de avisar.

**La puerta de FR-030 vive aquí**, no en un informe: una tabla cuyo sesgo contra
prosa de no nativo supere 2,0× no puede publicarse como umbral por defecto. Es
condición de bloqueo, no una nota al pie.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from nonio.backends.loader import ProfileMismatchError
from nonio.schema.enums import CorpusCategory

__all__ = ["CategoryStats", "CalibrationTable", "BiasGateError", "MAX_NON_NATIVE_FPR_RATIO"]

# FR-030 / SC-002. No es un parámetro afinable: es la promesa pública.
MAX_NON_NATIVE_FPR_RATIO = 2.0


class BiasGateError(RuntimeError):
    """La tabla supera el factor máximo de sesgo admitido (FR-030)."""


@dataclass(frozen=True)
class CategoryStats:
    threshold: float
    tpr: float
    fpr: float
    n_samples: int
    reproducible: bool


@dataclass(frozen=True)
class CalibrationTable:
    profile_id: str
    language: str
    min_words: int
    corpus_version: str
    per_category: dict[CorpusCategory, CategoryStats] = field(default_factory=dict)

    # ---- Artículo VIII / R-003 -------------------------------------------------

    def require_profile(self, profile_id: str) -> None:
        if profile_id != self.profile_id:
            raise ProfileMismatchError(
                f"La calibración es de {self.profile_id!r} y se intenta aplicar a "
                f"{profile_id!r}. Los umbrales no se transfieren entre perfiles (R-003)."
            )

    def require_language(self, language: str | None) -> None:
        if language != self.language:
            raise ProfileMismatchError(
                f"La calibración es de {self.language!r} y el texto es {language!r}. "
                "Extrapolar umbrales entre idiomas está prohibido (Artículo VIII)."
            )

    # ---- FR-030 ----------------------------------------------------------------

    def bias_ratio(self) -> float | None:
        """FP de español no nativo dividida entre la de humano general."""
        no_nativo = self.per_category.get(CorpusCategory.ESPANOL_NO_NATIVO)
        general = self.per_category.get(CorpusCategory.HUMANO_PRE2022)
        if not no_nativo or not general or general.fpr <= 0:
            return None
        return no_nativo.fpr / general.fpr

    def check_bias_gate(self, max_ratio: float = MAX_NON_NATIVE_FPR_RATIO) -> float:
        """Falla si el sesgo supera el factor admitido. Bloquea la publicación."""
        ratio = self.bias_ratio()
        if ratio is None:
            raise BiasGateError(
                "No se puede comprobar la puerta de FR-030: faltan las categorías "
                "espanol_no_nativo u humano_pre2022, o su FP es cero."
            )
        if ratio > max_ratio:
            raise BiasGateError(
                f"Sesgo contra prosa de no nativo {ratio:.2f}× > {max_ratio:.1f}×. "
                "FR-030 bloquea publicar este umbral por defecto. Opciones: subir el mínimo "
                "de longitud, endurecer el umbral aceptando más abstención, o publicar sin "
                "umbral por defecto."
            )
        return ratio

    # ---- Persistencia -----------------------------------------------------------

    def to_json(self) -> str:
        return json.dumps(
            {
                "profile_id": self.profile_id,
                "language": self.language,
                "min_words": self.min_words,
                "corpus_version": self.corpus_version,
                "per_category": {k.value: asdict(v) for k, v in self.per_category.items()},
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    @classmethod
    def from_path(cls, path: Path) -> CalibrationTable:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            profile_id=raw["profile_id"],
            language=raw["language"],
            min_words=raw["min_words"],
            corpus_version=raw["corpus_version"],
            per_category={
                CorpusCategory(k): CategoryStats(**v) for k, v in raw["per_category"].items()
            },
        )
