"""FR-029 / SC-003 — cada cifra declara si un tercero puede reproducirla.

El corpus privado no viaja con el repositorio. Sus cifras se publican junto a
las públicas, nunca en lugar de ellas, y marcadas como no reproducibles.
"""

from __future__ import annotations

from nonio.evaluation.calibrate import CaseMeasurement, fit_table
from nonio.evaluation.report import build_report
from nonio.schema.enums import CorpusCategory as C


def _ms(n=40):
    out = []
    for cat in (C.HUMANO_PRE2022, C.ESPANOL_NO_NATIVO, C.GENERADO):
        for i in range(n):
            out.append(
                CaseMeasurement(
                    case_id=f"{cat.value}-{i}",
                    category=cat,
                    word_count=300,
                    signals={"binoculars": i / n, "fast_detect_gpt": i / n},
                )
            )
    return out


def test_por_defecto_las_cifras_son_reproducibles():
    t = fit_table(_ms(), profile_id="p", language="es", corpus_version="v", min_words=250)
    assert all(s.reproducible for s in t.per_category.values())


def test_una_categoria_del_corpus_privado_se_marca():
    t = fit_table(
        _ms(),
        profile_id="p",
        language="es",
        corpus_version="v",
        min_words=250,
        reproducible={"espanol_no_nativo": False},
    )
    assert t.per_category[C.ESPANOL_NO_NATIVO].reproducible is False
    assert t.per_category[C.HUMANO_PRE2022].reproducible is True


def test_el_informe_propaga_la_marca():
    t = fit_table(
        _ms(),
        profile_id="p",
        language="es",
        corpus_version="v",
        min_words=250,
        reproducible={"espanol_no_nativo": False},
    )
    d = build_report(t).to_dict()
    assert d["per_category"]["espanol_no_nativo"]["reproducible"] is False
    texto = build_report(t).to_text()
    assert "no" in texto
