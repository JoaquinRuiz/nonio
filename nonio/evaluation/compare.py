"""Comparación de perfiles de medición lado a lado (issue #2, FR-021, R-003).

Los umbrales pertenecen al perfil y no se transfieren, así que comparar dos
perfiles no es aplicar el mismo número a los dos: es calibrar cada uno desde cero
y poner las tablas resultantes una al lado de la otra.

Se publican ambas **como salgan**. Si el perfil mayor no mejora, eso también es un
hallazgo y se publica igual: el valor del proyecto es la medición, no que el
resultado sea favorable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nonio.calibration.table import CalibrationTable
from nonio.evaluation.report import EvaluationReport, build_report
from nonio.schema.enums import CorpusCategory

__all__ = ["ProfileResult", "compare_reports", "render_comparison"]


@dataclass(frozen=True)
class ProfileResult:
    profile_id: str
    report: EvaluationReport
    runtime: dict[str, float] | None = None

    @property
    def tpr(self) -> float | None:
        st = self.report.per_category.get(CorpusCategory.GENERADO.value)
        return st["tpr"] if st else None

    @property
    def fpr_general(self) -> float | None:
        st = self.report.per_category.get(CorpusCategory.HUMANO_PRE2022.value)
        return st["fpr"] if st else None

    @property
    def fpr_no_nativo(self) -> float | None:
        st = self.report.per_category.get(CorpusCategory.ESPANOL_NO_NATIVO.value)
        return st["fpr"] if st else None


def compare_reports(resultados: list[ProfileResult]) -> dict:
    """Estructura comparable, sin agregar nada entre perfiles."""
    return {
        "profiles": [
            {
                "id": r.profile_id,
                "threshold": (
                    r.report.per_category.get(CorpusCategory.HUMANO_PRE2022.value, {}).get(
                        "threshold"
                    )
                ),
                "fpr_general": r.fpr_general,
                "fpr_non_native": r.fpr_no_nativo,
                "tpr_generated": r.tpr,
                "bias_ratio": r.report.bias_ratio,
                "bias_ci95": list(r.report.bias_ci) if r.report.bias_ci else None,
                "bias_verdict": r.report.bias_verdict,
                "runtime": r.runtime,
                "per_category": r.report.per_category,
            }
            for r in resultados
        ],
        "note": (
            "Los umbrales pertenecen al perfil y no se transfieren (R-003). Cada "
            "columna es una calibración independiente; no se promedian entre sí."
        ),
    }


def render_comparison(resultados: list[ProfileResult]) -> str:
    """Tabla legible. Nunca produce una cifra combinada entre perfiles."""

    def celda(v, pct=True):
        if v is None:
            return "   n/d"
        return f"{v:6.1%}" if pct else f"{v:6.3f}"

    anchura = max(len(r.profile_id) for r in resultados) + 2
    filas = [
        "métrica".ljust(26) + "".join(r.profile_id.ljust(anchura) for r in resultados),
        "-" * (26 + anchura * len(resultados)),
    ]

    def fila(nombre, fn):
        filas.append(nombre.ljust(26) + "".join(str(fn(r)).ljust(anchura) for r in resultados))

    fila(
        "umbral",
        lambda r: celda(
            r.report.per_category.get(CorpusCategory.HUMANO_PRE2022.value, {}).get("threshold"),
            pct=False,
        ),
    )
    fila("FP humano general", lambda r: celda(r.fpr_general))
    fila("FP español no nativo", lambda r: celda(r.fpr_no_nativo))
    fila("TPR generado", lambda r: celda(r.tpr))
    fila("sesgo", lambda r: f"{r.report.bias_ratio:6.2f}×" if r.report.bias_ratio else "   n/d")
    fila(
        "IC95% del sesgo",
        lambda r: (
            f"[{r.report.bias_ci[0]:.2f},{r.report.bias_ci[1]:.2f}]" if r.report.bias_ci else "n/d"
        ),
    )
    fila("veredicto FR-030", lambda r: r.report.bias_verdict or "n/d")
    fila(
        "mediana 1.000 palabras",
        lambda r: (f"{r.runtime['median_s']:.1f}s" if r.runtime else "sin medir"),
    )
    fila(
        "cumple SC-006 (≤30s)",
        lambda r: (("sí" if r.runtime["median_s"] <= 30 else "NO") if r.runtime else "sin medir"),
    )

    filas += [
        "",
        "Los umbrales pertenecen al perfil y no se transfieren (R-003): cada columna",
        "es una calibración independiente. No se promedian ni se combinan.",
    ]
    return "\n".join(filas)


def load_result(path: Path) -> ProfileResult:
    """Carga un artefacto de calibración guardado."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    tabla = CalibrationTable(
        profile_id=raw["profile_id"],
        language=raw["language"],
        min_words=raw["min_words"],
        corpus_version=raw["corpus_version"],
        per_category={},
    )
    ci = raw.get("bias", {}).get("ci95")
    rep = build_report(tabla, bias_ci=tuple(ci) if ci else None)
    return ProfileResult(profile_id=raw["profile_id"], report=rep)
