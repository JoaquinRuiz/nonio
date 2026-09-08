"""Informe HTML: FR-013, FR-024, y los Artículos I, II, V y IX."""

from __future__ import annotations

import re

import pytest

from nonio.config_author import AuthorLinks
from nonio.report_html import render_html
from nonio.schema.enums import AbstentionCause, CorpusCategory, Level
from nonio.schema.models import (
    Abstention,
    AnalysisResult,
    Block,
    DocumentInfo,
    ProfileInfo,
    Reading,
    Signal,
)

SIG = (
    Signal(
        name="binoculars",
        raw_value=0.81,
        normalized_value=0.94,
        expected_range=(0.55, 1.10),
        validated_languages=("es",),
    ),
)
PROF = ProfileInfo(
    id="qwen2.5-0.5b",
    observer_model="Qwen/Qwen2.5-0.5B@x",
    performer_model="Qwen/Qwen2.5-0.5B-Instruct@x",
    validated_languages=("es",),
)
DOC = DocumentInfo(
    source="ensayo.md", detected_language="es", measurable_word_count=800, excluded_ratio=0.12
)


def _res(result):
    return AnalysisResult(
        nonio_version="0.1.0",
        profile=PROF,
        document=DOC,
        result=result,
        blocks=(
            Block(
                index=0,
                start=0,
                end=10,
                token_count=200,
                result=Reading(
                    level=Level.BAJO,
                    signals=SIG,
                    applied_threshold=0.9,
                    measured_fpr=0.05,
                    fpr_category=CorpusCategory.HUMANO_PRE2022,
                    fpr_reproducible=True,
                ),
            ),
        ),
    )


_LECTURA = Reading(
    level=Level.ALTO,
    signals=SIG,
    applied_threshold=0.9167,
    measured_fpr=0.053,
    fpr_category=CorpusCategory.HUMANO_PRE2022,
    fpr_reproducible=True,
)
_ABST = Abstention(
    cause=AbstentionCause.INSUFFICIENT_LENGTH, detail="90 palabras; mínimo 300.", observed=90
)


# --- Artículo V: nada sale de la máquina, tampoco al abrir el informe ---------


@pytest.mark.parametrize("r", [_LECTURA, _ABST])
def test_el_informe_no_carga_ningun_recurso_externo(r):
    """Un recurso remoto delataría a quien lo sirve que se analizó un texto."""
    doc = render_html(_res(r))
    externos = re.findall(r'(?:src|href)\s*=\s*"(https?://[^"]+)"', doc)
    # Solo se admiten enlaces del autor, que son navegación explícita, no carga.
    assert not externos, f"recursos externos: {externos}"


def test_sin_enlaces_de_autor_no_hay_seccion_de_promocion():
    """Se busca el elemento, no la cadena: `promo` está en el CSS siempre."""
    assert '<section class="promo">' not in render_html(_res(_LECTURA), author=AuthorLinks())


# --- Artículo IX: no debe parecer un certificado -------------------------------


def test_el_aviso_va_antes_que_la_cifra():
    doc = render_html(_res(_LECTURA))
    assert doc.index("no debe ser base única") < doc.index("señal alto")


def test_no_hay_lenguaje_de_certificado():
    """Afirmaciones, no palabras sueltas.

    «Esto no es un veredicto» contiene la palabra y es exactamente lo que el
    informe debe decir. Buscar el término suelto marcaría como infracción su
    propia negación.
    """
    doc = render_html(_res(_LECTURA)).lower()
    afirmaciones = [
        r"(?<!no )(?<!no es un )certifica",
        r"se acredita",
        r"el presente dictamen",
        r"(?<!no es un )veredicto:",
        r"firmado por",
    ]
    for patron in afirmaciones:
        assert not re.search(patron, doc), f"aspecto de certificado: {patron!r}"


def test_el_informe_niega_ser_un_veredicto():
    """La negación sí debe estar, y arriba."""
    doc = render_html(_res(_LECTURA))
    assert "no es un veredicto" in doc.lower()


def test_la_promocion_se_declara_ajena_a_la_medicion():
    links = AuthorLinks(name="X", youtube_url="https://youtube.com/@x")
    doc = render_html(_res(_LECTURA), author=links)
    assert "No forman parte de la medición" in doc


# --- Artículo III: la cifra nunca va sola --------------------------------------


def test_toda_lectura_muestra_umbral_y_tasa_de_error():
    doc = render_html(_res(_LECTURA))
    assert "0.9167" in doc and "5.3%" in doc and "humano_pre2022" in doc


def test_se_muestra_el_porcentaje_excluido():
    assert "12.0%" in render_html(_res(_LECTURA))


# --- Artículos I y II ----------------------------------------------------------


def test_ninguna_afirmacion_de_autoria():
    doc = render_html(_res(_LECTURA)).lower()
    for frase in ("escrito por ia", "written by ai", "es humano", "es ia"):
        assert frase not in doc


def test_la_abstencion_se_presenta_como_resultado_completo():
    doc = render_html(_res(_ABST))
    assert "insufficient_evidence" in doc
    assert "no un fallo" in doc, "la abstención debe presentarse como resultado, no como error"
    assert "insufficient_length" in doc


def test_el_html_es_valido_y_autocontenido():
    doc = render_html(_res(_LECTURA))
    assert doc.startswith("<!doctype html>") and doc.rstrip().endswith("</html>")
    assert "<style>" in doc, "el CSS va embebido"


def test_el_texto_analizado_se_escapa():
    """Un documento con HTML dentro no debe inyectarse en el informe."""
    doc = render_html(_res(_LECTURA), text="<script>alert(1)</script>" + "x " * 50)
    assert "<script>alert(1)</script>" not in doc
