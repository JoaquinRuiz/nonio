"""Artículo III — nunca una cifra agregada sin desglose por categoría.

No basta con que el informe incluya el desglose: no debe existir ninguna vía
—bandera, parámetro o campo— para obtener una precisión global. La media esconde
justo el daño de este dominio.
"""

from __future__ import annotations

import inspect
import json

import pytest

from nonio.calibration.table import CalibrationTable, CategoryStats
from nonio.evaluation import report as report_mod
from nonio.evaluation.report import build_report
from nonio.schema.enums import CorpusCategory

pytestmark = pytest.mark.contract


def _table(fpr_general=0.04, fpr_no_nativo=0.06) -> CalibrationTable:
    def st(fpr, tpr=0.0):
        return CategoryStats(threshold=0.8, tpr=tpr, fpr=fpr, n_samples=120, reproducible=True)

    return CalibrationTable(
        profile_id="qwen2.5-0.5b",
        language="es",
        min_words=250,
        corpus_version="test",
        per_category={
            CorpusCategory.HUMANO_PRE2022: st(fpr_general),
            CorpusCategory.ESPANOL_NO_NATIVO: st(fpr_no_nativo),
            CorpusCategory.GENERADO: st(0.0, tpr=0.82),
            CorpusCategory.TECNICA_ESTRUCTURADA: st(0.07),
        },
    )


def test_el_informe_desglosa_por_categoria():
    d = build_report(_table()).to_dict()
    assert set(d["per_category"]) >= {"humano_pre2022", "espanol_no_nativo", "generado"}
    for stats in d["per_category"].values():
        assert {"tpr", "fpr", "n_samples", "threshold"} <= set(stats)


def test_no_existe_ningun_campo_de_precision_global():
    payload = json.dumps(build_report(_table()).to_dict())
    for prohibido in (
        '"accuracy"',
        '"overall"',
        '"global_accuracy"',
        '"mean_fpr"',
        '"average"',
        '"total_accuracy"',
    ):
        assert prohibido not in payload, f"Artículo III: aparece {prohibido}"


def test_no_hay_funcion_que_produzca_un_agregado():
    """Ni siquiera como utilidad interna que alguien pueda exponer luego."""
    fuente = inspect.getsource(report_mod)
    for sospechoso in ("def overall", "def accuracy", "def global_", "def mean_"):
        assert sospechoso not in fuente


def test_cada_cifra_declara_si_es_reproducible():
    """SC-003 / FR-029: el corpus privado no viaja con el repositorio."""
    d = build_report(_table()).to_dict()
    for stats in d["per_category"].values():
        assert isinstance(stats["reproducible"], bool)


def test_el_informe_publica_la_puerta_de_sesgo():
    """FR-031: el veredicto exige intervalo, no solo el punto."""
    d = build_report(_table(0.04, 0.06), bias_ci=(1.1, 1.8)).to_dict()
    assert d["bias"]["ratio_non_native_vs_general"] == pytest.approx(1.5)
    assert d["bias"]["ci95"] == [1.1, 1.8]
    assert d["bias"]["verdict"] == "pasa"
    assert d["bias"]["passes"] is True
    assert d["bias"]["requirement"] == "FR-030"


def test_el_informe_marca_el_bloqueo_cuando_se_supera_el_factor():
    d = build_report(_table(0.03, 0.09), bias_ci=(2.4, 4.1)).to_dict()
    assert d["bias"]["verdict"] == "bloquea"
    assert d["bias"]["passes"] is False
    assert "BLOQUEA" in build_report(_table(0.03, 0.09), bias_ci=(2.4, 4.1)).to_text()


def test_el_informe_declara_no_concluyente_si_el_intervalo_cruza():
    """El caso realmente medido: punto 1,30x, IC95% [0,78 – 2,53]."""
    r = build_report(_table(0.053, 0.069), bias_ci=(0.78, 2.53))
    assert r.to_dict()["bias"]["verdict"] == "no_concluyente"
    assert r.to_dict()["bias"]["passes"] is False
    assert "NO CONCLUYENTE" in r.to_text() and "más muestra" in r.to_text()


def test_las_categorias_ausentes_se_declaran():
    """Que falte una categoría del Artículo VII no puede pasar inadvertido."""
    d = build_report(_table()).to_dict()
    assert "mixto" in d["missing_categories"]


def test_el_informe_expone_la_fp_absoluta_junto_al_cociente():
    """FR-030 solo limita el cociente; la cifra absoluta debe ser visible.

    Un umbral bajo que acuse por igual a todo el mundo da cociente 1,00x y pasa
    la puerta siendo inútil. Documentado en docs/calibration-findings.md.
    """
    d = build_report(_table(0.18, 0.18), bias_ci=(0.8, 1.3)).to_dict()
    assert d["bias"]["passes"] is True, "cociente 1,0x: la puerta pasa"
    assert d["bias"]["absolute_fpr_general"] == 0.18, "y la FP absoluta es visible"
    texto = build_report(_table(0.18, 0.18), bias_ci=(0.8, 1.3)).to_text()
    assert "18.0%" in texto and "inútil" in texto
