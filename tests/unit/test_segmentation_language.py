from __future__ import annotations

from nonio.language.detect import detect_language
from nonio.segmentation.blocks import segment

ES = (
    "La medición de señales estadísticas sobre texto exige cautela metodológica. "
    "Ninguna cifra aislada sostiene una conclusión sobre la procedencia de un escrito. "
    "Por eso el instrumento reporta su margen de error junto a cada lectura que emite. "
)


def test_los_bloques_cubren_el_texto_sin_solaparse():
    texto = "\n\n".join([ES] * 5)
    bloques = segment(texto, min_words=20)
    for a, b in zip(bloques, bloques[1:], strict=False):
        assert a.end <= b.start


def test_los_offsets_apuntan_al_texto_original():
    texto = "\n\n".join([ES] * 4)
    for b in segment(texto, min_words=20):
        assert texto[b.start : b.end] == b.text


def test_los_parrafos_cortos_se_funden():
    texto = "Uno.\n\nDos.\n\nTres.\n\n" + ES
    bloques = segment(texto, min_words=30)
    assert len(bloques) < 4


def test_texto_vacio_no_da_bloques():
    assert segment("") == []


def test_detecta_espanol():
    assert detect_language(ES) == "es"


def test_texto_demasiado_corto_no_afirma_idioma():
    """Preferible None que acertar por azar: acaba en abstención por idioma."""
    assert detect_language("Hola.") is None


def test_detecta_otros_idiomas():
    fi = (
        "Tilastollisten signaalien mittaaminen tekstistä vaatii menetelmällistä "
        "varovaisuutta ja huolellisuutta aina kaikissa tapauksissa."
    )
    assert detect_language(fi) == "fi"


def test_ruido_no_se_afirma_como_idioma():
    """El umbral se compara contra probabilidad normalizada, no log-prob cruda."""
    assert detect_language("asdf qwer zxcv hjkl uiop") is None
