"""Tramos contribuyentes (FR-005) y emparejamiento de categoría (FR-009)."""

from __future__ import annotations

from nonio.reading.category import match_category
from nonio.schema.enums import CorpusCategory


def test_prosa_narrativa_empareja_con_humano_general():
    texto = (
        "Cuando desperté, el patio estaba lleno de hojas secas que nadie había barrido. "
        "Mi abuela decía que barrer en martes traía mala suerte, y aunque yo no creía en eso, "
        "tampoco me atrevía a contradecirla aquella mañana de noviembre."
    )
    assert match_category(texto) is CorpusCategory.HUMANO_PRE2022


def test_prosa_muy_estructurada_empareja_con_tecnica():
    texto = (
        "El procedimiento consta de tres fases:\n"
        "1. Preparación de la muestra\n"
        "2. Medición del caudal\n"
        "3. Registro de resultados\n\n"
        "Como se observa en la tabla 2, el error relativo se mantiene por debajo del 5 %."
    )
    assert match_category(texto) is CorpusCategory.TECNICA_ESTRUCTURADA


def test_mucho_marcado_excluido_implica_documento_tecnico():
    """SC-008: si se excluyó mucho, el registro es casi seguro técnico."""
    assert (
        match_category("texto cualquiera", excluded_ratio=0.35)
        is CorpusCategory.TECNICA_ESTRUCTURADA
    )


def test_el_emparejamiento_no_perfila_a_la_persona():
    """Artículo IX: Nonio observa el registro del texto, nunca quién lo escribe.

    No existe ninguna vía para emparejar con `espanol_no_nativo`: eso exigiría
    inferir algo sobre el autor, que es exactamente lo que el artículo prohíbe.
    """
    import inspect

    from nonio.reading import category

    fuente = inspect.getsource(category)
    assert "ESPANOL_NO_NATIVO" not in fuente
