"""Escenarios 4, 5, 6 y 9 de la spec: las rutas de abstención de `analyze()`.

Son los que se pueden verificar sin calibración publicada. Los escenarios 1, 2, 3
y 7 —que exigen una lectura— dependen de la tabla de calibración y quedan para
cuando exista, porque el Artículo III impide emitir lectura sin ella.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nonio.calibration.table import CalibrationTable, CategoryStats
from nonio.schema.enums import AbstentionCause, CorpusCategory

FIX = Path(__file__).resolve().parents[1] / "fixtures"

pytestmark = [pytest.mark.integration, pytest.mark.needs_models]


def _tabla(min_words: int = 300, language: str = "es") -> CalibrationTable:
    st = CategoryStats(threshold=0.8, tpr=0.8, fpr=0.04, n_samples=100, reproducible=True)
    return CalibrationTable(
        profile_id="qwen2.5-0.5b",
        language=language,
        min_words=min_words,
        corpus_version="test",
        per_category={
            CorpusCategory.HUMANO_PRE2022: st,
            CorpusCategory.TECNICA_ESTRUCTURADA: st,
        },
    )


@pytest.fixture(scope="module")
def nonio_mod():
    pytest.importorskip("torch")
    import nonio

    try:
        nonio.analyze("hola " * 400, table=_tabla())
    except nonio.ResourceUnavailableError:
        pytest.skip("recursos de medición no descargados")
    return nonio


def test_escenario_4_texto_corto_se_abstiene_por_longitud(nonio_mod):
    r = nonio_mod.analyze(FIX / "es_90_palabras.txt", table=_tabla())
    assert r.result.type == "insufficient_evidence"
    assert r.result.cause is AbstentionCause.INSUFFICIENT_LENGTH
    assert r.result.observed is not None and r.result.required == 300
    assert not hasattr(r.result, "level")


def test_escenario_5_idioma_sin_calibracion_se_abstiene(nonio_mod):
    """Y forzar --language no autoriza a extrapolar (Artículo VIII)."""
    texto = FIX.joinpath("es_largo.txt").read_text(encoding="utf-8")
    r = nonio_mod.analyze(texto, language="fi", table=_tabla())
    assert r.result.cause is AbstentionCause.UNCALIBRATED_LANGUAGE


def test_sin_calibracion_no_hay_lectura(nonio_mod):
    """Artículo III: ninguna cifra sin su tasa de error medida."""
    r = nonio_mod.analyze(FIX / "es_largo.txt", table=None)
    assert r.result.type == "insufficient_evidence"
    assert r.result.cause is AbstentionCause.UNCALIBRATED_LANGUAGE


def test_fr028_la_exclusion_es_causa_distinta_de_la_longitud(nonio_mod):
    """Un documento largo que queda corto tras excluir código dice por qué."""
    prosa = FIX.joinpath("es_largo.txt").read_text(encoding="utf-8")
    doc = "```python\n" + ("x = 1\n" * 400) + "```\n\n" + " ".join(prosa.split()[:60])
    r = nonio_mod.analyze(doc, table=_tabla(min_words=200))
    assert r.result.type == "insufficient_evidence"
    assert r.result.cause is AbstentionCause.INSUFFICIENT_AFTER_EXCLUSION
    assert r.document.excluded_ratio > 0.5


def test_la_salida_nunca_afirma_autoria(nonio_mod):
    """Escenario 7 / SC-005, también en la ruta de abstención."""
    import json

    r = nonio_mod.analyze(FIX / "es_90_palabras.txt", table=_tabla())
    payload = json.loads(r.model_dump_json())

    def claves(n, acc=None):
        acc = acc if acc is not None else set()
        if isinstance(n, dict):
            for k, v in n.items():
                acc.add(k)
                claves(v, acc)
        elif isinstance(n, list):
            for v in n:
                claves(v, acc)
        return acc

    prohibidas = {"is_ai", "ai_generated", "human_written", "author", "verdict"}
    assert not (claves(payload) & prohibidas)
