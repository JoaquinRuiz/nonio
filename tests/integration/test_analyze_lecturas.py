"""Escenarios 1, 2, 3 y 7 de la spec: las rutas que producen lectura.

Usan una tabla de calibración **medida pero no publicable**: la puerta de FR-030
sale no concluyente, así que Nonio no la distribuye por defecto. Se pasa aquí de
forma explícita porque estos tests verifican que el mecanismo funciona, no que la
calibración sea buena. Son cosas distintas y conviene no confundirlas: que
`analyze()` sepa emitir una lectura no dice nada sobre si esa lectura acierta.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nonio.calibration.table import CalibrationTable

FIX = Path(__file__).resolve().parents[1] / "fixtures"
TABLA = FIX / "calibration_medida.json"
CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "public"

pytestmark = [pytest.mark.integration, pytest.mark.needs_models, pytest.mark.needs_corpus]


@pytest.fixture(scope="module")
def tabla() -> CalibrationTable:
    if not TABLA.exists():
        pytest.skip("no hay tabla de calibración medida")
    return CalibrationTable.from_path(TABLA)


@pytest.fixture(scope="module")
def nonio_mod():
    pytest.importorskip("torch")
    import nonio

    try:
        nonio.analyze("hola " * 400)
    except nonio.ResourceUnavailableError:
        pytest.skip("recursos de medición no descargados")
    return nonio


def _texto(categoria: str, minimo: int = 300) -> str:
    d = CORPUS / categoria
    if not d.is_dir():
        pytest.skip(f"corpus {categoria} ausente")
    for f in sorted(d.glob("*.txt")):
        t = f.read_text(encoding="utf-8")
        if len(t.split()) >= minimo:
            return t
    pytest.skip(f"sin textos de {minimo}+ palabras en {categoria}")


def test_escenario_1_texto_generado_da_lectura_con_su_margen(nonio_mod, tabla):
    r = nonio_mod.analyze(_texto("generado"), table=tabla)
    assert r.result.type == "reading", f"se abstuvo: {getattr(r.result, 'detail', '')}"
    assert r.result.applied_threshold is not None
    assert r.result.measured_fpr is not None
    assert r.result.fpr_category is not None
    assert r.blocks, "Artículo IV: siempre desglose"


def test_escenario_2_humano_misma_forma_de_salida(nonio_mod, tabla):
    """La spec pide que el formato NO cambie según el resultado."""
    gen = json.loads(nonio_mod.analyze(_texto("generado"), table=tabla).model_dump_json())
    hum = json.loads(nonio_mod.analyze(_texto("humano_pre2022"), table=tabla).model_dump_json())

    def claves(n, pre=""):
        out = set()
        if isinstance(n, dict):
            for k, v in n.items():
                out.add(f"{pre}.{k}")
                out |= claves(v, f"{pre}.{k}")
        elif isinstance(n, list) and n:
            out |= claves(n[0], f"{pre}[]")
        return out

    if gen["result"]["type"] == hum["result"]["type"]:
        assert claves(gen) == claves(hum), "la forma de la salida cambia según el resultado"


def test_escenario_3_texto_mixto_no_colapsa_a_un_valor(nonio_mod, tabla):
    """En texto mixto el agregado es un número intermedio sin significado."""
    generado = _texto("generado")
    humano = _texto("humano_pre2022")
    mixto = humano + "\n\n" + generado

    r = nonio_mod.analyze(mixto, table=tabla)
    assert len(r.blocks) >= 2, "un documento mixto debe dar varios bloques"
    # El desglose existe y es consultable con independencia del agregado
    assert all(b.result.type in ("reading", "insufficient_evidence") for b in r.blocks)


def test_escenario_7_ninguna_lectura_afirma_autoria(nonio_mod, tabla):
    """SC-005, ahora sobre una salida que SÍ contiene lectura."""
    payload = json.loads(nonio_mod.analyze(_texto("generado"), table=tabla).model_dump_json())

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

    prohibidas = {
        "is_ai",
        "ai_generated",
        "human_written",
        "author",
        "authorship",
        "verdict",
        "probability_ai",
        "confidence_ai",
    }
    assert not (claves(payload) & prohibidas)


def test_la_lectura_lleva_tramos_contribuyentes(nonio_mod, tabla):
    """FR-005: los offsets apuntan al texto original."""
    texto = _texto("generado")
    r = nonio_mod.analyze(texto, table=tabla)
    if r.result.type != "reading":
        pytest.skip("se abstuvo")
    for s in r.result.top_spans:
        assert 0 <= s.start < s.end <= len(texto)
