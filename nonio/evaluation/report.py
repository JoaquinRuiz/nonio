"""Informe de evaluación por categoría (FR-021, FR-023, Artículo III).

**No existe ninguna vía para emitir una cifra agregada sin desglose.** No es que
esté desaconsejada: no hay bandera, ni parámetro, ni función que la produzca. La
precisión media esconde precisamente el daño que este dominio causa —el sesgo
contra prosa de no nativos y contra escritura técnica muy estructurada— y el
Artículo III lo prohíbe expresamente.

Cada cifra declara además si es reproducible por un tercero, porque el corpus
privado no viaja con el repositorio (FR-029, SC-003).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nonio.calibration.table import MAX_NON_NATIVE_FPR_RATIO, CalibrationTable
from nonio.schema.enums import CorpusCategory

__all__ = ["EvaluationReport", "build_report"]


@dataclass(frozen=True)
class EvaluationReport:
    profile_id: str
    language: str
    min_words: int
    corpus_version: str
    per_category: dict[str, dict[str, Any]]
    bias_ratio: float | None
    bias_ci: tuple[float, float] | None
    bias_verdict: str | None
    absolute_fpr: float | None
    bias_gate_max: float
    bias_gate_passes: bool | None
    missing_categories: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "language": self.language,
            "min_words": self.min_words,
            "corpus_version": self.corpus_version,
            "per_category": self.per_category,
            "bias": {
                "ratio_non_native_vs_general": self.bias_ratio,
                "ci95": list(self.bias_ci) if self.bias_ci else None,
                "verdict": self.bias_verdict,
                "absolute_fpr_general": self.absolute_fpr,
                "max_allowed": self.bias_gate_max,
                "passes": self.bias_gate_passes,
                "requirement": "FR-030",
                "note": (
                    "FR-030 restringe el cociente, no la tasa absoluta. Un umbral bajo "
                    "que acuse por igual a todo el mundo pasa la puerta siendo inútil; "
                    "mira absolute_fpr_general antes de fiarte del cociente."
                ),
            },
            "missing_categories": self.missing_categories,
            "note": (
                "No se publica precisión agregada: el Artículo III exige desglose por "
                "categoría porque la media esconde el sesgo contra prosa de no nativos y "
                "contra escritura técnica muy estructurada."
            ),
        }

    def to_text(self) -> str:
        anchura = max((len(k) for k in self.per_category), default=10)
        lineas = [
            f"Perfil {self.profile_id}  ·  idioma {self.language}  ·  "
            f"min_words={self.min_words}  ·  corpus {self.corpus_version}",
            "",
            f"{'categoría'.ljust(anchura)}   n      umbral    TPR      FPR     reproducible",
        ]
        for nombre, st in sorted(self.per_category.items()):
            lineas.append(
                f"{nombre.ljust(anchura)}  {st['n_samples']:5d}  {st['threshold']:8.4f}  "
                f"{st['tpr']:6.3f}  {st['fpr']:6.3f}   {'sí' if st['reproducible'] else 'no'}"
            )
        lineas.append("")
        if self.bias_ratio is None:
            lineas.append("Puerta FR-030: NO EVALUABLE — faltan categorías para calcular el sesgo.")
        else:
            ic = f" IC95% [{self.bias_ci[0]:.2f}, {self.bias_ci[1]:.2f}]" if self.bias_ci else ""
            estado = {
                "pasa": "PASA",
                "bloquea": "BLOQUEA LA PUBLICACIÓN",
                "no_concluyente": "NO CONCLUYENTE — el intervalo cruza el límite",
            }.get(self.bias_verdict or "", "SIN VEREDICTO")
            lineas.append(
                f"Puerta FR-030: sesgo no nativo/general = {self.bias_ratio:.2f}×{ic} "
                f"(máximo {self.bias_gate_max:.1f}×) → {estado}"
            )
            if self.bias_verdict == "no_concluyente":
                lineas.append("  No habilita publicar umbral por defecto: hace falta más muestra.")
            if self.absolute_fpr is not None:
                lineas.append(
                    f"  FP absoluta sobre texto humano general: {self.absolute_fpr:.1%}. "
                    "FR-030 no la limita; un cociente bajo con FP alta es un detector "
                    "equitativo e inútil."
                )
        if self.missing_categories:
            lineas.append("Categorías ausentes del corpus: " + ", ".join(self.missing_categories))
        return "\n".join(lineas)


def build_report(
    table: CalibrationTable, *, bias_ci: tuple[float, float] | None = None
) -> EvaluationReport:
    ratio = table.bias_ratio()
    verdict = None
    if ratio is not None:
        if bias_ci is None:
            # Sin intervalo no hay veredicto (FR-031). No se degrada a comparar
            # el punto: eso es justo lo que el requisito prohíbe.
            verdict = "sin_intervalo"
        else:
            verdict = table.bias_gate_verdict(bias_ci[0], bias_ci[1]).verdict
    faltan = [c.value for c in CorpusCategory if c not in table.per_category]
    return EvaluationReport(
        profile_id=table.profile_id,
        language=table.language,
        min_words=table.min_words,
        corpus_version=table.corpus_version,
        per_category={
            c.value: {
                "threshold": s.threshold,
                "tpr": s.tpr,
                "fpr": s.fpr,
                "n_samples": s.n_samples,
                "reproducible": s.reproducible,
            }
            for c, s in table.per_category.items()
        },
        bias_ratio=ratio,
        bias_ci=bias_ci,
        bias_verdict=verdict,
        absolute_fpr=table.absolute_fpr(),
        bias_gate_max=MAX_NON_NATIVE_FPR_RATIO,
        bias_gate_passes=(None if verdict is None else verdict == "pasa"),
        missing_categories=faltan,
    )
