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

__all__ = [
    "CategoryStats",
    "CalibrationTable",
    "BiasGateError",
    "BiasGateVerdict",
    "MAX_NON_NATIVE_FPR_RATIO",
]

# FR-030 / SC-002. No es un parámetro afinable: es la promesa pública.
MAX_NON_NATIVE_FPR_RATIO = 2.0


class BiasGateError(RuntimeError):
    """La tabla no supera la puerta de sesgo (FR-030)."""


@dataclass(frozen=True)
class BiasGateVerdict:
    """Veredicto de la puerta con su incertidumbre (FR-030 + FR-031).

    Tres estados, no dos. Comparar el punto estimado contra el techo es lo que
    FR-031 prohíbe: un cociente de 1,30x cuyo IC95% va de 0,78 a 2,53 no
    demuestra que se cumpla el límite, solo que no se ha demostrado lo contrario.
    Declarar `no_concluyente` es la lectura honesta, y encaja con la spec, que
    admite ese tercer estado en SC-002 en vez de forzar cumplido/incumplido.
    """

    ratio: float
    ci_low: float
    ci_high: float
    n_reference: int
    n_non_native: int
    max_ratio: float

    @property
    def verdict(self) -> str:
        if self.ci_high <= self.max_ratio:
            return "pasa"
        if self.ci_low > self.max_ratio:
            return "bloquea"
        return "no_concluyente"

    @property
    def publishable(self) -> bool:
        """Solo se publica umbral por defecto si la puerta pasa de verdad.

        `no_concluyente` no habilita publicar: el Artículo III exige la cifra
        medida, y una cifra cuyo intervalo cruza el límite no está medida con la
        precisión que el límite necesita.
        """
        return self.verdict == "pasa"

    def explain(self) -> str:
        base = (
            f"sesgo {self.ratio:.2f}× IC95% [{self.ci_low:.2f}, {self.ci_high:.2f}] "
            f"(máximo {self.max_ratio:.1f}×), sobre {self.n_reference} casos de "
            f"referencia y {self.n_non_native} de no nativo"
        )
        if self.verdict == "pasa":
            return f"PASA — {base}"
        if self.verdict == "bloquea":
            return f"BLOQUEA LA PUBLICACIÓN — {base}"
        return (
            f"NO CONCLUYENTE — {base}. El intervalo cruza el límite: hace falta más "
            "muestra para decidir. No habilita publicar umbral por defecto."
        )


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

    def absolute_fpr(self) -> float | None:
        """FP sobre texto humano general, en términos absolutos.

        FR-030 restringe solo el **cociente** entre categorías, no esta cifra. Es
        un agujero de la salvaguarda: un umbral bajo que acuse por igual a todo el
        mundo da un cociente perfecto de 1,00x y pasa la puerta mientras señala
        falsamente a una de cada cinco personas. Medido: con umbral 0,85 el sesgo
        es 1,00x y la FP absoluta 18,3%.

        Se expone para que ese caso sea visible en el informe. Enmendar FR-030
        para añadir un techo absoluto es decisión de spec, no de una task, así que
        la puerta se deja como está especificada. Ver docs/calibration-findings.md.
        """
        general = self.per_category.get(CorpusCategory.HUMANO_PRE2022)
        return general.fpr if general else None

    def check_bias_gate(self, max_ratio: float = MAX_NON_NATIVE_FPR_RATIO) -> float:
        """Falla si el sesgo puntual supera el factor admitido.

        Conserva la semántica de dos estados para quien solo necesita el punto.
        Para decidir si se puede publicar usa `bias_gate_verdict()`, que tiene en
        cuenta la incertidumbre como exige FR-031.
        """
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

    def bias_gate_verdict(
        self, ci_low: float, ci_high: float, max_ratio: float = MAX_NON_NATIVE_FPR_RATIO
    ) -> BiasGateVerdict:
        """Veredicto con incertidumbre (FR-031). El intervalo lo calcula quien mide."""
        ratio = self.bias_ratio()
        if ratio is None:
            raise BiasGateError(
                "No se puede comprobar la puerta de FR-030: faltan categorías o su FP es cero."
            )
        general = self.per_category[CorpusCategory.HUMANO_PRE2022]
        no_nativo = self.per_category[CorpusCategory.ESPANOL_NO_NATIVO]
        return BiasGateVerdict(
            ratio=ratio,
            ci_low=ci_low,
            ci_high=ci_high,
            n_reference=general.n_samples,
            n_non_native=no_nativo.n_samples,
            max_ratio=max_ratio,
        )

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
