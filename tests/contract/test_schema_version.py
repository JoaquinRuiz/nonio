"""Artículo VI — el versionado del esquema es independiente del paquete."""

from __future__ import annotations

import pytest

from nonio.schema.export import SCHEMA_VERSION, output_schema

pytestmark = pytest.mark.contract


def test_schema_version_es_semver():
    partes = SCHEMA_VERSION.split(".")
    assert len(partes) == 3 and all(p.isdigit() for p in partes)


def test_schema_version_no_se_deriva_de_la_version_del_paquete():
    """Artículo VI: son dos versionados con reglas propias.

    Pueden coincidir por azar, así que no se compara el valor: se comprueba que
    el esquema no lee la versión del paquete para construir la suya.
    """
    import inspect

    import nonio.schema.export as export
    import nonio.schema.models as models

    fuente = inspect.getsource(models) + inspect.getsource(export)
    assert "importlib.metadata" not in fuente
    assert "__version__" not in fuente


def test_el_esquema_declara_su_version():
    assert output_schema()["x-schema-version"] == SCHEMA_VERSION


def test_el_esquema_incluye_los_campos_obligatorios_del_articulo_3():
    defs = output_schema()["$defs"]
    reading = defs["Reading"]["required"]
    for campo in ("applied_threshold", "measured_fpr", "fpr_category"):
        assert campo in reading, f"Artículo III: {campo} no es obligatorio en el esquema"
