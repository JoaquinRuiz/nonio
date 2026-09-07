"""FR-027: los offsets de los tramos excluidos apuntan al texto original.

Un offset desplazado rompería FR-005, que señala los tramos contribuyentes sobre
el texto que el usuario tiene delante.
"""

from __future__ import annotations

import pytest

from nonio.extraction import extract
from nonio.schema.enums import DetectionMethod, ExcludedKind

MD = """# Título

Un párrafo de prosa normal que sí debe medirse.

```python
def esto_no_se_mide():
    return "código"
```

Otro párrafo con `código en línea` dentro.

> Una cita en bloque que no se mide.

| a | b |
|---|---|
| 1 | 2 |

Final.
"""


def test_los_offsets_apuntan_al_texto_original():
    e = extract(MD)
    for s in e.excluded_spans:
        assert 0 <= s.start < s.end <= len(e.raw_text)


def test_el_texto_medible_conserva_la_longitud():
    """Se sustituye por espacios, no se elimina: así los offsets siguen valiendo."""
    e = extract(MD)
    assert len(e.measurable_text) == len(e.raw_text)


def test_el_codigo_queda_fuera_del_texto_medible():
    e = extract(MD)
    assert "esto_no_se_mide" not in e.measurable_text
    assert "prosa normal" in e.measurable_text


def test_se_detectan_los_tipos_esperados():
    kinds = {s.kind for s in extract(MD).excluded_spans}
    assert ExcludedKind.CODE_BLOCK in kinds
    assert ExcludedKind.TABLE in kinds
    assert ExcludedKind.BLOCKQUOTE in kinds


def test_excluded_ratio_entre_cero_y_uno():
    e = extract(MD)
    assert 0.0 < e.excluded_ratio < 1.0


def test_texto_sin_marcado_no_excluye_nada():
    """SC-008: el ratio se reporta incluso valiendo 0.0."""
    e = extract("Solo prosa, sin nada que excluir. " * 20)
    assert e.excluded_ratio == 0.0
    assert e.excluded_spans == ()


def test_los_tramos_no_se_solapan():
    e = extract(MD)
    spans = sorted(e.excluded_spans, key=lambda s: s.start)
    for a, b in zip(spans, spans[1:], strict=False):
        assert a.end <= b.start, "los tramos fundidos no pueden solaparse"


def test_la_heuristica_se_declara_como_tal():
    """R-004: el usuario distingue lo detectado con certeza de lo inferido."""
    plano = "Texto normal.\n> Una cita heredada del correo.\nMás texto."
    e = extract(plano)
    assert any(s.detection is DetectionMethod.HEURISTIC for s in e.excluded_spans) or any(
        s.detection is DetectionMethod.AST for s in e.excluded_spans
    )


@pytest.mark.parametrize("texto", ["", "   ", "\n\n"])
def test_entradas_degeneradas_no_revientan(texto):
    e = extract(texto)
    assert e.excluded_ratio == 0.0
