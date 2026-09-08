"""El paquete distribuible cumple lo que promete (FR-022, SC-003, Artículo VI).

Un fallo de empaquetado no lo detecta ningún test de lógica: el código puede
estar perfecto y el paquete instalado no funcionar. Ya pasó — el entry point
apuntaba a `app`, que devuelve el parser en vez de ejecutarlo, y `nonio` habría
salido a PyPI imprimiendo un ArgumentParser y devolviendo error.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
with (RAIZ / "pyproject.toml").open("rb") as _fh:
    PYPROJECT = tomllib.load(_fh)

pytestmark = pytest.mark.contract


def test_el_entry_point_apunta_a_una_funcion_ejecutable():
    """No a una que construya el parser y lo devuelva."""
    destino = PYPROJECT["project"]["scripts"]["nonio"]
    modulo, _, funcion = destino.partition(":")
    assert funcion == "main", f"el entry point debe ser main(), no {funcion!r}"

    import importlib

    fn = getattr(importlib.import_module(modulo), funcion)
    assert fn(["schema", "--version"]) == 0, "main() debe devolver un código de salida int"


def test_los_metadatos_minimos_de_pypi_estan():
    p = PYPROJECT["project"]
    for campo in ("name", "version", "description", "readme", "requires-python", "license"):
        assert p.get(campo), f"falta {campo}"
    assert p["urls"].get("Homepage") and p["urls"].get("Issues")
    assert len(p["classifiers"]) >= 8


def test_la_licencia_declarada_coincide_con_el_fichero():
    assert (RAIZ / "LICENSE").exists()
    texto = (RAIZ / "LICENSE").read_text(encoding="utf-8")[:2000]
    assert "Apache License" in texto
    assert any("Apache" in c for c in PYPROJECT["project"]["classifiers"])


def test_el_corpus_no_viaja_como_miles_de_ficheros_sueltos():
    """20 MB en 5.214 ficheros haría la instalación lenta sin cambiar ninguna cifra."""
    wheel = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert "force-include" not in wheel, "el corpus suelto no debe ir en el wheel"
    assert any("jsonl.gz" in a for a in wheel.get("artifacts", []))


def test_el_corpus_empaquetado_existe_y_esta_equilibrado():
    from nonio.evaluation.bundle import BUNDLE_CAP, load_bundle

    ruta = RAIZ / "nonio" / "_corpus" / "corpus.jsonl.gz"
    if not ruta.exists():
        pytest.skip("corpus no empaquetado; ejecuta python -m nonio.evaluation.bundle")
    assert ruta.stat().st_size < 5_000_000, "el paquete no debe superar unos pocos MB"

    from collections import Counter

    casos = load_bundle(ruta)
    cuenta = Counter(c.category.value for c, _ in casos)
    assert len(cuenta) >= 3, "el corpus debe cubrir varias categorías"
    for cat, n in cuenta.items():
        assert n <= BUNDLE_CAP, f"{cat} supera el tope de {BUNDLE_CAP}"


def test_todo_caso_distribuido_es_redistribuible():
    """No se puede publicar en PyPI texto que no se pueda redistribuir (FR-029)."""
    from nonio.evaluation.bundle import load_bundle

    ruta = RAIZ / "nonio" / "_corpus" / "corpus.jsonl.gz"
    if not ruta.exists():
        pytest.skip("corpus no empaquetado")
    for caso, _ in load_bundle(ruta):
        assert caso.redistributable, f"{caso.id} no es redistribuible"
        assert caso.license, f"{caso.id} sin licencia declarada"


def test_la_version_del_paquete_y_la_del_esquema_son_independientes():
    """Artículo VI: dos versionados con reglas propias."""
    import inspect

    import nonio

    assert nonio.__version__ == PYPROJECT["project"]["version"]
    # No se comparan valores —pueden coincidir por azar— sino que el esquema no
    # lee la versión del paquete para construir la suya.
    from nonio.schema import export, models

    fuente = inspect.getsource(models) + inspect.getsource(export)
    assert "importlib.metadata" not in fuente
    assert "__version__" not in fuente
