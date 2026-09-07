"""Exportación del JSON Schema de la salida (FR-013, FR-015).

`schema_version` se versiona aparte de la versión del paquete (Artículo VI):
añadir campo es MINOR, quitar campo o cambiar el significado de uno existente es
MAJOR, el resto es PATCH.
"""

from __future__ import annotations

from typing import Any

from nonio.schema.models import SCHEMA_VERSION, AnalysisResult

__all__ = ["SCHEMA_VERSION", "output_schema"]


def output_schema() -> dict[str, Any]:
    """Devuelve el JSON Schema de `AnalysisResult`.

    Equivale al comando `nonio schema`. La capacidad vive aquí, no en la CLI
    (Artículo VI).
    """
    schema = AnalysisResult.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "nonio.AnalysisResult"
    schema["x-schema-version"] = SCHEMA_VERSION
    return schema
