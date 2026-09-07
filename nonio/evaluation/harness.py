"""Harness de evaluación reejecutable por terceros (FR-022, SC-003).

Vive dentro del paquete, no en un `eval/` hermano, por dos razones: el
Artículo VI exige que `nonio eval` tenga equivalente importable, y un directorio
hermano no viajaría con `pip install`, dejando a un tercero sin poder reproducir
las cifras.
"""

from __future__ import annotations

from pathlib import Path

from nonio.backends.loader import load_pair
from nonio.calibration.corpus import load_manifest
from nonio.calibration.table import CalibrationTable
from nonio.evaluation.calibrate import fit_table, measure_cases, selection_bias
from nonio.evaluation.report import EvaluationReport, build_report
from nonio.schema.enums import CorpusCategory

__all__ = ["evaluate", "corpus_root", "manifest_path"]

DEFAULT_MIN_WORDS = 250


def _package_corpus() -> Path | None:
    cand = Path(__file__).resolve().parent.parent / "_corpus"
    return cand if (cand / "manifest.jsonl").exists() else None


def corpus_root(root: Path | None = None) -> Path:
    """Corpus del repositorio si existe; si no, el que viaja con el paquete."""
    if root is not None:
        return root
    repo = Path.cwd() / "corpus"
    if (repo / "manifest.jsonl").exists():
        return repo
    pkg = _package_corpus()
    if pkg:
        return pkg
    raise FileNotFoundError(
        "No se encontró el corpus. Ensámblalo con nonio.evaluation.build_corpus."
    )


def manifest_path(root: Path | None = None) -> Path:
    return corpus_root(root) / "manifest.jsonl"


def evaluate(
    *,
    corpus: str = "public",
    profile: str | None = None,
    root: Path | None = None,
    min_words: int = DEFAULT_MIN_WORDS,
    limit_per_category: int | None = 120,
) -> EvaluationReport:
    """Ejecuta la evaluación y devuelve el informe por categoría.

    Equivale al comando `nonio eval`. Nunca devuelve una cifra global.
    """
    base = corpus_root(root)
    cases = load_manifest(base / "manifest.jsonl")
    if corpus == "public":
        cases = [c for c in cases if c.redistributable]
    elif corpus == "private":
        cases = [c for c in cases if not c.redistributable]

    pair = load_pair(profile)
    measurements = measure_cases(
        cases, base / "public", pair, limit_per_category=limit_per_category
    )
    table = fit_table(
        measurements,
        profile_id=pair.profile.id,
        language="es",
        corpus_version=_corpus_version(base),
        min_words=min_words,
    )
    return build_report(table)


def _corpus_version(base: Path) -> str:
    import hashlib

    h = hashlib.sha1((base / "manifest.jsonl").read_bytes()).hexdigest()[:8]
    return f"manifest-{h}"


def bias_report(measurements, category: CorpusCategory, min_words: int) -> dict[str, float]:
    """Expone el sesgo de selección que introduce el mínimo elegido."""
    return selection_bias(measurements, category, min_words)


def load_table(path: Path) -> CalibrationTable:
    return CalibrationTable.from_path(path)
