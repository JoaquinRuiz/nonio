"""El manifiesto del corpus es parte del producto (Artículo VII, FR-029)."""

from __future__ import annotations

from pathlib import Path

import pytest

from nonio.backends.profiles import PROFILES
from nonio.calibration.corpus import load_manifest
from nonio.schema.enums import CorpusCategory

MANIFEST = Path(__file__).resolve().parents[2] / "corpus" / "manifest.jsonl"
ROOT = MANIFEST.parent / "public"

pytestmark = pytest.mark.needs_corpus


@pytest.fixture(scope="module")
def cases():
    if not MANIFEST.exists():
        pytest.skip("corpus no ensamblado; ver nonio.evaluation.build_corpus")
    return load_manifest(MANIFEST)


def test_todo_caso_declara_licencia_y_procedencia(cases):
    """El corpus público es de licencia mixta: sin esto no es redistribuible."""
    for c in cases:
        assert c.license, f"{c.id} sin licencia"
        assert c.provenance, f"{c.id} sin procedencia"


def test_los_textos_existen(cases):
    for c in cases[:200]:
        assert (ROOT / Path(c.text_path).name).exists() or (ROOT / c.text_path).exists()


def test_ningun_generado_usa_la_familia_de_un_perfil(cases):
    """R-006: si no, las cifras estarían infladas por construcción."""
    familias = {p.observer_model.split("/")[0] for p in PROFILES.values()}
    for c in cases:
        c.validate_against_profiles(familias)


def test_el_corpus_publico_es_redistribuible(cases):
    for c in cases:
        assert c.redistributable, f"{c.id} no redistribuible dentro del corpus público"


def test_no_nativo_excluye_hablantes_de_herencia(cases):
    """Un hablante de herencia no es un hablante no nativo."""
    nn = [c for c in cases if c.category is CorpusCategory.ESPANOL_NO_NATIVO]
    assert nn, "no hay casos de español no nativo"
    for c in nn:
        assert "l1='spanish'" not in c.provenance.lower()
