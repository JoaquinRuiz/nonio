"""Artículo III — Calibración medida y publicada.

Toda lectura lleva umbral, FP medida y categoría emparejada. No es un campo
opcional que se pueda omitir: sin ellos la lectura no se puede construir.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from nonio.schema.enums import CorpusCategory, Level
from nonio.schema.models import Reading

from ._helpers import SIGNALS, analysis

pytestmark = pytest.mark.contract

OBLIGATORIOS = ["applied_threshold", "measured_fpr", "fpr_category"]


@pytest.mark.parametrize("campo", OBLIGATORIOS)
def test_no_se_puede_construir_una_lectura_sin_su_margen(campo):
    kwargs = {
        "level": Level.ALTO,
        "signals": SIGNALS,
        "applied_threshold": 0.72,
        "measured_fpr": 0.031,
        "fpr_category": CorpusCategory.HUMANO_PRE2022,
        "fpr_reproducible": True,
    }
    del kwargs[campo]
    with pytest.raises(ValidationError):
        Reading(**kwargs)


@pytest.mark.parametrize("campo", OBLIGATORIOS)
def test_los_campos_no_admiten_nulo(campo):
    kwargs = {
        "level": Level.ALTO,
        "signals": SIGNALS,
        "applied_threshold": 0.72,
        "measured_fpr": 0.031,
        "fpr_category": CorpusCategory.HUMANO_PRE2022,
        "fpr_reproducible": True,
        campo: None,
    }
    with pytest.raises(ValidationError):
        Reading(**kwargs)


def test_toda_lectura_serializada_lleva_su_margen():
    """Recorre el árbol entero: documento y cada bloque."""
    payload = json.loads(analysis().model_dump_json())
    resultados = [payload["result"]] + [b["result"] for b in payload["blocks"]]
    for r in resultados:
        if r["type"] != "reading":
            continue
        for campo in OBLIGATORIOS:
            assert r.get(campo) is not None, f"Artículo III: lectura sin {campo}"


def test_cada_lectura_reporta_el_valor_de_cada_senal():
    """FR-003: el valor individual de cada señal, además de la lectura combinada."""
    payload = json.loads(analysis().model_dump_json())
    assert len(payload["result"]["signals"]) >= 2
    for s in payload["result"]["signals"]:
        assert "raw_value" in s and "normalized_value" in s


def test_fpr_declara_si_es_reproducible():
    """SC-003 / FR-029: el usuario debe saber si la cifra viene del corpus público."""
    payload = json.loads(analysis().model_dump_json())
    assert isinstance(payload["result"]["fpr_reproducible"], bool)
