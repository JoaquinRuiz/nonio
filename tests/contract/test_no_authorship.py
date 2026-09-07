"""Artículo I — Instrumento, no juez.

Ninguna salida afirma autoría. El test recorre TODAS las rutas del JSON, no una
lista de campos esperados: así una adición futura descuidada también falla.
"""

from __future__ import annotations

import json

import pytest

from nonio.schema.export import output_schema

from ._helpers import abstention, analysis

FORBIDDEN = {
    "is_ai",
    "ai_generated",
    "human_written",
    "author",
    "authorship",
    "verdict",
    "probability_ai",
    "confidence_ai",
    "is_human",
    "ai_score",
}

pytestmark = pytest.mark.contract


def _all_keys(node, acc=None):
    acc = acc if acc is not None else set()
    if isinstance(node, dict):
        for k, v in node.items():
            acc.add(k)
            _all_keys(v, acc)
    elif isinstance(node, list):
        for v in node:
            _all_keys(v, acc)
    return acc


@pytest.mark.parametrize("result", [None, abstention()])
def test_ninguna_clave_de_autoria_en_la_salida(result):
    payload = json.loads(analysis(result).model_dump_json())
    offending = _all_keys(payload) & FORBIDDEN
    assert not offending, f"Artículo I violado: claves de autoría {offending}"


def test_ninguna_clave_de_autoria_en_el_esquema():
    """Ni siquiera como campo declarado pero no emitido."""
    offending = _all_keys(output_schema()) & FORBIDDEN
    assert not offending, f"Artículo I violado en el esquema: {offending}"


def test_extra_fields_rechazados():
    """Un `is_ai` añadido por descuido revienta en validación, no pasa en silencio."""
    from pydantic import ValidationError

    from nonio.schema.models import Reading

    with pytest.raises(ValidationError):
        Reading(**{**json.loads(analysis().result.model_dump_json()), "is_ai": True})
