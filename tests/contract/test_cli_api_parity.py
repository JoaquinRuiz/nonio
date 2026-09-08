"""Artículo VI — ninguna capacidad existe solo en la CLI.

La paridad se verifica, no se promete: el test recorre el registro real de
comandos, así que un comando nuevo sin equivalente importable lo rompe.
"""

from __future__ import annotations

import pytest

import nonio
from nonio.cli.exit_codes import ExitCode
from nonio.cli.main import app

pytestmark = pytest.mark.contract

# Comando de la CLI -> símbolo público equivalente.
EQUIVALENTES = {
    "analyze": "analyze",
    "profiles": "profiles",
    "check": "check_resources",
    "download": "download_profile",
    "schema": "output_schema",
    "eval": "evaluate",
}


def _comandos() -> list[str]:
    sub = app()._subparsers._group_actions[0]
    return sorted(sub.choices)


def test_todo_comando_tiene_equivalente_importable():
    for cmd in _comandos():
        assert cmd in EQUIVALENTES, f"comando {cmd!r} sin equivalente declarado"
        nombre = EQUIVALENTES[cmd]
        assert hasattr(nonio, nombre), f"{cmd!r} no tiene nonio.{nombre}()"
        assert nombre in nonio.__all__, f"nonio.{nombre} no está en __all__"


def test_no_sobran_equivalentes():
    """Si se retira un comando, su entrada debe retirarse también."""
    assert set(_comandos()) == set(EQUIVALENTES)


def test_la_superficie_publica_es_importable():
    for nombre in nonio.__all__:
        assert hasattr(nonio, nombre), f"{nombre} en __all__ pero no importable"


def test_la_abstencion_tiene_codigo_propio_distinto_del_fallo():
    """FR-014: 'este texto no se puede medir' != 'tu entorno falla'."""
    assert ExitCode.INSUFFICIENT_EVIDENCE != ExitCode.OK
    assert ExitCode.INSUFFICIENT_EVIDENCE not in (
        ExitCode.USAGE,
        ExitCode.RESOURCE_UNAVAILABLE,
        ExitCode.INTERNAL,
    )


def test_analyze_no_lanza_excepcion_por_propiedades_del_texto():
    """Artículo II: la abstención viaja como resultado, no como excepción."""
    import inspect

    from nonio import core

    fuente = inspect.getsource(core.analyze)
    assert "raise Abstention" not in fuente
    assert "_abstain(" in fuente
