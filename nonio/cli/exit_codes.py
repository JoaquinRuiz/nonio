"""Códigos de salida (FR-014).

La distinción que pide FR-014 es entre *este texto no se puede medir* y *tu
entorno falla*. Son cosas distintas y un script debe poder tratarlas distinto:
lo primero es un resultado legítimo del instrumento, lo segundo es un problema de
la máquina.
"""

from __future__ import annotations

from enum import IntEnum

__all__ = ["ExitCode"]


class ExitCode(IntEnum):
    OK = 0
    #: Abstención. NO es un fallo (Artículo II): va acompañada de un
    #: AnalysisResult válido cuyo resultado es `insufficient_evidence`.
    INSUFFICIENT_EVIDENCE = 1
    USAGE = 2
    RESOURCE_UNAVAILABLE = 3
    INTERNAL = 4
