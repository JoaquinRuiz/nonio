"""Artículo II — La abstención es una salida de primera clase.

`insufficient_evidence` es un resultado válido y completo, no un fallo. El token
lo nombra el artículo literalmente, así que tiene que aparecer en el contrato
serializado; `cause` es la subcategoría, no el nombre del resultado.
"""

from __future__ import annotations

import json

import pytest

from nonio.schema.enums import AbstentionCause
from nonio.schema.models import Abstention

from ._helpers import abstention, analysis

pytestmark = pytest.mark.contract


def test_el_token_es_el_que_nombra_la_constitucion():
    payload = json.loads(abstention().model_dump_json())
    assert payload["type"] == "insufficient_evidence"


def test_la_abstencion_no_expone_nivel_ni_como_nulo():
    payload = json.loads(abstention().model_dump_json())
    assert "level" not in payload, "Artículo II: la abstención no tiene nivel"
    assert not hasattr(Abstention, "level")


def test_las_cuatro_causas_son_distinguibles():
    """FR-007, FR-008 y FR-028: cada causa se reporta por separado."""
    causas = {c.value for c in AbstentionCause}
    assert causas == {
        "insufficient_length",
        "insufficient_after_exclusion",
        "uncalibrated_language",
        "signal_disagreement",
    }


def test_longitud_y_exclusion_son_causas_distintas():
    """FR-028: 'el documento es corto' no es 'lo que quedó tras excluir es corto'."""
    assert AbstentionCause.INSUFFICIENT_LENGTH is not AbstentionCause.INSUFFICIENT_AFTER_EXCLUSION


def test_toda_abstencion_lleva_causa_y_detalle():
    payload = json.loads(abstention().model_dump_json())
    assert payload["cause"] and payload["detail"]


def test_desacuerdo_entre_senales_muestra_cada_valor():
    """Escenario 6: el usuario ve el valor de cada señal que discrepa."""
    from ._helpers import SIGNALS

    a = Abstention(
        cause=AbstentionCause.SIGNAL_DISAGREEMENT,
        detail="binoculars alto, fast_detect_gpt bajo; ambas superan el margen.",
        signals=SIGNALS,
    )
    payload = json.loads(a.model_dump_json())
    assert len(payload["signals"]) == 2


def test_los_bloques_pueden_abstenerse_sin_que_lo_haga_el_documento():
    payload = json.loads(analysis().model_dump_json())
    assert payload["result"]["type"] == "reading"
    assert any(b["result"]["type"] == "insufficient_evidence" for b in payload["blocks"])
