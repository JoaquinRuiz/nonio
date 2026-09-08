"""V12 y V13 del quickstart: el harness sobre el corpus público (FR-021, FR-030)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nonio.calibration.table import CalibrationTable
from nonio.evaluation.calibrate import CaseMeasurement, bias_ci, fit_table
from nonio.evaluation.report import build_report
from nonio.schema.enums import CorpusCategory as C

FIX = Path(__file__).resolve().parents[1] / "fixtures"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def informe():
    """Informe construido desde la tabla medida, sin volver a medir el corpus.

    Medirlo entero cuesta media hora; el test comprueba el contrato del informe,
    que es lo que puede romperse en un cambio de código.
    """
    if not (FIX / "calibration_medida.json").exists():
        pytest.skip("no hay tabla medida")
    t = CalibrationTable.from_path(FIX / "calibration_medida.json")
    return build_report(t, bias_ci=(0.78, 2.53))


def test_v12_el_informe_lista_las_categorias_con_sus_cifras(informe):
    d = informe.to_dict()
    assert len(d["per_category"]) >= 3
    for nombre, st in d["per_category"].items():
        assert st["n_samples"] > 0, f"{nombre} sin casos"
        assert 0.0 <= st["fpr"] <= 1.0
        assert "reproducible" in st


def test_v12_no_hay_cifra_agregada(informe):
    payload = json.dumps(informe.to_dict())
    for prohibido in ('"accuracy"', '"overall"', '"mean_fpr"', '"global'):
        assert prohibido not in payload


def test_v13_el_cociente_de_sesgo_es_calculable_y_lleva_intervalo(informe):
    b = informe.to_dict()["bias"]
    assert b["ratio_non_native_vs_general"] is not None
    assert b["ci95"] is not None, "FR-031: nunca sin intervalo"
    assert b["verdict"] in ("pasa", "bloquea", "no_concluyente")


def test_las_categorias_ausentes_se_declaran(informe):
    """`mixto` no existe todavía; el informe debe decirlo, no callarlo."""
    assert "mixto" in informe.to_dict()["missing_categories"]


def test_el_veredicto_actual_no_habilita_publicar(informe):
    """Estado real del proyecto: no concluyente, y eso no es 'pasa'."""
    d = informe.to_dict()["bias"]
    assert d["verdict"] == "no_concluyente"
    assert d["passes"] is False


def test_la_tabla_lleva_las_nulas_necesarias_para_normalizar():
    """Sin distribuciones nulas no hay percentil, y sin percentil no hay lectura."""
    t = CalibrationTable.from_path(FIX / "calibration_medida.json")
    assert t.null_distributions, "la tabla debe llevar las nulas"
    for señal in ("binoculars", "fast_detect_gpt"):
        assert len(t.null_distributions[señal]) > 100


def test_el_bootstrap_devuelve_un_intervalo_ordenado():
    ms = [
        CaseMeasurement(
            case_id=f"{cat.value}-{i}",
            category=cat,
            word_count=300,
            signals={"binoculars": i / 50, "fast_detect_gpt": i / 50},
        )
        for cat in (C.HUMANO_PRE2022, C.ESPANOL_NO_NATIVO)
        for i in range(50)
    ]
    t = fit_table(ms, profile_id="p", language="es", corpus_version="v", min_words=250)
    med, lo, hi = bias_ci(ms, threshold=t.per_category[C.HUMANO_PRE2022].threshold, min_words=250)
    assert lo <= med <= hi
