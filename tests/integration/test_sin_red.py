"""Artículo V — el texto analizado nunca sale de la máquina.

En vez de tirar la interfaz de red, se parchea el socket para que **cualquier**
conexión saliente lance excepción, y se comprueba que `analyze()` no la provoca
nunca. Es más fuerte que apagar el wifi: detecta también un intento de conexión
que hubiera fallado en silencio.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "es_largo.txt"

pytestmark = [pytest.mark.integration, pytest.mark.needs_models]


class RedProhibidaError(AssertionError):
    """Se intentó abrir una conexión durante el análisis."""


@pytest.fixture
def sin_red(monkeypatch):
    def bloquear(*args, **kwargs):
        raise RedProhibidaError("analyze() intentó salir a red (Artículo V)")

    monkeypatch.setattr(socket.socket, "connect", bloquear)
    monkeypatch.setattr(socket.socket, "connect_ex", bloquear)
    monkeypatch.setattr(socket, "create_connection", bloquear)
    return True


def test_analyze_no_abre_ninguna_conexion(sin_red):
    pytest.importorskip("torch")
    import nonio

    try:
        result = nonio.analyze(FIXTURE)
    except nonio.ResourceUnavailableError:
        pytest.skip("recursos de medición no descargados")
    assert result.schema_version
    assert result.document.detected_language == "es"


def test_la_deteccion_de_idioma_es_local(sin_red):
    from nonio.language.detect import detect_language

    texto = FIXTURE.read_text(encoding="utf-8")
    assert detect_language(texto) == "es"


def test_la_extraccion_es_local(sin_red):
    from nonio.extraction import extract

    e = extract(FIXTURE.read_text(encoding="utf-8"))
    assert e.measurable_word_count > 0
