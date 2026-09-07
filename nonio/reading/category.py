"""Emparejamiento de categoría para la tasa de falsos positivos (FR-009).

Toda lectura va acompañada de la FP medida sobre **la categoría de texto más
parecida a la entrada**. Emparejar mal no es un detalle estético: significa
acompañar la lectura de un margen de error que no le corresponde.

El emparejamiento es deliberadamente conservador. Nonio no sabe si quien escribe
es hablante nativo —ni debe intentar averiguarlo, que sería perfilar a una
persona (Artículo IX)—. Lo único que observa es el registro del texto. Cuando no
hay señal clara de registro técnico, se empareja con la categoría humana general.
"""

from __future__ import annotations

import re

from nonio.schema.enums import CorpusCategory

__all__ = ["match_category"]

# Marcas de prosa expositiva muy estructurada: la que el Artículo III señala como
# propensa a falsos positivos.
_TECNICA = (
    re.compile(r"^\s*(\d+\.|\-|\*|•)\s", re.MULTILINE),  # listas
    re.compile(r"\b(figura|tabla|ecuación|apartado|sección)\s+\d+", re.IGNORECASE),
    re.compile(r"[=<>±∑∫√]|\b\d+\s*(%|kg|km|ms|MB|GB)\b"),
)


def match_category(text: str, *, excluded_ratio: float = 0.0) -> CorpusCategory:
    """Elige la categoría de corpus con la que emparejar el margen de error."""
    # Mucho marcado excluido implica documento técnico casi con seguridad.
    if excluded_ratio >= 0.20:
        return CorpusCategory.TECNICA_ESTRUCTURADA

    marcas = sum(1 for patron in _TECNICA if patron.search(text))
    if marcas >= 2:
        return CorpusCategory.TECNICA_ESTRUCTURADA
    return CorpusCategory.HUMANO_PRE2022
