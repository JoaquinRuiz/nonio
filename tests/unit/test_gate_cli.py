"""La puerta de FR-030 sobre un artefacto guardado, sin modelos ni corpus."""

from __future__ import annotations

import json

import pytest

from nonio.evaluation.gate import check_artifact


def _art(tmp_path, **bias):
    base = {
        "ratio_non_native_vs_general": 1.3,
        "ci95": [0.78, 2.53],
        "verdict": "no_concluyente",
        "absolute_fpr_general": 0.053,
        "max_allowed": 2.0,
    }
    base.update(bias)
    p = tmp_path / "cal.json"
    p.write_text(json.dumps({"bias": base, "missing_categories": ["mixto"]}))
    return p


def test_pasa_devuelve_cero(tmp_path):
    code, msg = check_artifact(_art(tmp_path, verdict="pasa", ci95=[0.9, 1.6]))
    assert code == 0 and "pasa" in msg


def test_bloquea_devuelve_uno(tmp_path):
    """Único caso que rompe la integración continua."""
    code, msg = check_artifact(_art(tmp_path, verdict="bloquea", ci95=[2.4, 4.1]))
    assert code == 1 and "BLOQUEA" in msg


def test_no_concluyente_avisa_pero_pasa(tmp_path):
    """Es el estado real del proyecto.

    Dejar la integración continua en rojo de forma permanente convertiría el rojo
    en ruido y nadie miraría el siguiente. Se avisa y se pasa, con seguimiento en
    una issue.
    """
    code, msg = check_artifact(_art(tmp_path))
    assert code == 0
    assert "NO CONCLUYENTE" in msg and "No habilita publicar" in msg


def test_un_cociente_sin_intervalo_falla(tmp_path):
    """FR-031: sin intervalo no es una medida."""
    code, msg = check_artifact(_art(tmp_path, ci95=None))
    assert code == 1 and "FR-031" in msg


def test_el_mensaje_expone_la_fp_absoluta(tmp_path):
    """FR-030 no la limita; leer el cociente sin ella induce a error."""
    _, msg = check_artifact(_art(tmp_path))
    assert "5.3%" in msg


def test_las_categorias_ausentes_se_declaran(tmp_path):
    _, msg = check_artifact(_art(tmp_path))
    assert "mixto" in msg


def test_un_artefacto_que_no_existe_falla(tmp_path):
    code, msg = check_artifact(tmp_path / "no-existe.json")
    assert code == 1 and "No existe" in msg


def test_el_artefacto_versionado_del_repo_es_valido():
    """El que ejecuta la integración continua de verdad."""
    from pathlib import Path

    p = Path(__file__).resolve().parents[2] / "calibration" / "qwen2.5-0.5b-es.json"
    if not p.exists():
        pytest.skip("sin artefacto de calibración")
    code, _ = check_artifact(p)
    assert code == 0, "el artefacto del repo dejaría la CI en rojo"
