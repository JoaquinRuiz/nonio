"""Calibración, puerta de sesgo y criterio de desacuerdo."""

from __future__ import annotations

import pytest

from nonio.backends.loader import ProfileMismatchError
from nonio.calibration.corpus import CorpusCase, GeneratorConflictError
from nonio.calibration.table import BiasGateError, CalibrationTable, CategoryStats
from nonio.reading.combine import combine, normalize
from nonio.schema.enums import AbstentionCause, CorpusCategory, Level
from nonio.schema.models import Signal


def _stats(fpr: float, threshold: float = 0.8) -> CategoryStats:
    return CategoryStats(threshold=threshold, tpr=0.85, fpr=fpr, n_samples=200, reproducible=True)


def _table(fpr_general: float = 0.03, fpr_no_nativo: float = 0.05) -> CalibrationTable:
    return CalibrationTable(
        profile_id="qwen2.5-0.5b",
        language="es",
        min_words=300,
        corpus_version="2026.09",
        per_category={
            CorpusCategory.HUMANO_PRE2022: _stats(fpr_general),
            CorpusCategory.ESPANOL_NO_NATIVO: _stats(fpr_no_nativo),
        },
    )


def _signal(name: str, normalized: float) -> Signal:
    return Signal(
        name=name,
        raw_value=0.0,
        normalized_value=normalized,
        expected_range=(0.0, 1.0),
        validated_languages=("es",),
    )


# --- R-003: los umbrales pertenecen al perfil -----------------------------------


def test_no_se_aplica_la_calibracion_de_un_perfil_a_otro():
    with pytest.raises(ProfileMismatchError):
        _table().require_profile("salamandra-2b")


def test_no_se_extrapola_entre_idiomas():
    """Artículo VIII: antes abstenerse que reutilizar umbrales de otro idioma."""
    with pytest.raises(ProfileMismatchError):
        _table().require_language("en")


# --- FR-030: la puerta del 2,0x --------------------------------------------------


def test_la_puerta_pasa_por_debajo_del_factor():
    assert _table(0.03, 0.05).check_bias_gate() == pytest.approx(5 / 3)


def test_la_puerta_bloquea_por_encima_del_factor():
    with pytest.raises(BiasGateError, match="FR-030"):
        _table(0.03, 0.09).check_bias_gate()


def test_el_limite_exacto_no_bloquea():
    assert _table(0.03, 0.06).check_bias_gate() == pytest.approx(2.0)


def test_sin_las_categorias_necesarias_la_puerta_falla_en_vez_de_pasar():
    """Que falte el dato no puede leerse como que el sesgo es aceptable."""
    tabla = CalibrationTable(
        profile_id="qwen2.5-0.5b", language="es", min_words=300, corpus_version="x"
    )
    with pytest.raises(BiasGateError):
        tabla.check_bias_gate()


# --- R-009: combinación y desacuerdo ---------------------------------------------


def test_senales_de_acuerdo_producen_lectura_con_su_margen():
    r = combine(
        [_signal("binoculars", 0.95), _signal("fast_detect_gpt", 0.90)],
        _table(),
        CorpusCategory.HUMANO_PRE2022,
    )
    assert isinstance(r, type(r)) and r.type == "reading"
    assert r.level is Level.ALTO
    assert r.applied_threshold == 0.8
    assert r.measured_fpr == 0.03
    assert r.fpr_category is CorpusCategory.HUMANO_PRE2022


def test_senales_contrarias_con_margen_producen_abstencion():
    r = combine(
        [_signal("binoculars", 0.98), _signal("fast_detect_gpt", 0.60)],
        _table(),
        CorpusCategory.HUMANO_PRE2022,
    )
    assert r.type == "insufficient_evidence"
    assert r.cause is AbstentionCause.SIGNAL_DISAGREEMENT
    assert r.signals is not None and len(r.signals) == 2


def test_un_desacuerdo_trivial_no_es_un_desacuerdo():
    """Ambas pegadas al umbral: es ruido, no contradicción."""
    r = combine(
        [_signal("binoculars", 0.81), _signal("fast_detect_gpt", 0.79)],
        _table(),
        CorpusCategory.HUMANO_PRE2022,
    )
    assert r.type == "reading"


def test_la_abstencion_por_desacuerdo_muestra_el_valor_de_cada_senal():
    """Escenario 6 de la spec."""
    r = combine(
        [_signal("binoculars", 0.99), _signal("fast_detect_gpt", 0.50)],
        _table(),
        CorpusCategory.HUMANO_PRE2022,
    )
    assert "binoculars=0.99" in r.detail and "fast_detect_gpt=0.50" in r.detail


def test_normalize_devuelve_percentil():
    nula = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    assert normalize(0.45, nula) == pytest.approx(0.5)
    assert normalize(-1.0, nula) == 0.0
    assert normalize(99.0, nula) == 1.0


# --- R-006: el corpus generado no puede usar la familia que puntúa ---------------


def test_un_caso_generado_con_la_familia_del_perfil_se_rechaza():
    caso = CorpusCase(
        id="gen-001",
        category=CorpusCategory.GENERADO,
        text_path="generado/gen-001.txt",
        provenance="generado por el proyecto",
        license="Apache-2.0",
        redistributable=True,
        generator="Qwen/Qwen2.5-7B",
    )
    with pytest.raises(GeneratorConflictError, match="inflad"):
        caso.validate_against_profiles({"Qwen", "BSC-LT"})


def test_un_caso_generado_con_otra_familia_se_acepta():
    caso = CorpusCase(
        id="gen-002",
        category=CorpusCategory.GENERADO,
        text_path="generado/gen-002.txt",
        provenance="generado por el proyecto",
        license="Apache-2.0",
        redistributable=True,
        generator="mistralai/Mistral-7B-v0.3",
    )
    caso.validate_against_profiles({"Qwen", "BSC-LT"})


def test_un_caso_generado_debe_declarar_su_generador():
    caso = CorpusCase(
        id="gen-003",
        category=CorpusCategory.GENERADO,
        text_path="generado/gen-003.txt",
        provenance="desconocida",
        license="Apache-2.0",
        redistributable=True,
    )
    with pytest.raises(ValueError, match="generador"):
        caso.validate_against_profiles({"Qwen"})
