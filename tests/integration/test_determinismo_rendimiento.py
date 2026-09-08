"""FR-006 (determinismo) y SC-006 (presupuesto de tiempo interactivo)."""

from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest

FIX = Path(__file__).resolve().parents[1] / "fixtures"

pytestmark = [pytest.mark.integration, pytest.mark.needs_models]


@pytest.fixture(scope="module")
def entorno():
    pytest.importorskip("torch")
    from nonio.backends.determinism import configure_determinism
    from nonio.backends.loader import ResourceUnavailableError, load_pair

    configure_determinism()
    try:
        return load_pair()
    except ResourceUnavailableError:
        pytest.skip("recursos de medición no descargados")


def _doc(palabras: int) -> str:
    base = (
        "El instrumento no decide autoría. Estima señales estadísticas asociadas a la "
        "generación automática de lenguaje y las reporta junto a su incertidumbre, de modo "
        "que quien lea el resultado pueda discutirlo en lugar de acatarlo. "
    )
    texto = base * (palabras // len(base.split()) + 1)
    return " ".join(texto.split()[:palabras])


def test_fr006_mismo_texto_mismo_resultado(entorno):
    """Determinismo por máquina y configuración. Entre máquinas aplica SC-003."""
    from nonio.signals.engine import measure

    doc = _doc(400)
    a = measure(doc, entorno).aggregate(0, len(doc))
    b = measure(doc, entorno).aggregate(0, len(doc))
    assert a == b, f"FR-006 violado: {a} != {b}"


def test_fr006_el_determinismo_aguanta_entre_documentos(entorno):
    """Medir otro texto en medio no debe alterar el resultado del primero."""
    from nonio.signals.engine import measure

    doc = _doc(300)
    a = measure(doc, entorno).aggregate(0, len(doc))
    measure(_doc(500), entorno)
    b = measure(doc, entorno).aggregate(0, len(doc))
    assert a == b


@pytest.mark.benchmark
def test_sc006_mil_palabras_en_cpu(entorno):
    """Mediana ≤ 30 s y p95 ≤ 60 s para 1.000 palabras sin GPU."""
    from nonio.signals.engine import measure

    doc = _doc(1000)
    tiempos = []
    for _ in range(5):
        t0 = time.perf_counter()
        measure(doc, entorno)
        tiempos.append(time.perf_counter() - t0)

    mediana = statistics.median(tiempos)
    p95 = sorted(tiempos)[-1]
    print(f"\n  SC-006: mediana {mediana:.1f}s   p95 {p95:.1f}s   ({len(doc.split())} palabras)")
    assert mediana <= 30.0, f"mediana {mediana:.1f}s supera los 30 s de SC-006"
    assert p95 <= 60.0, f"p95 {p95:.1f}s supera los 60 s de SC-006"
