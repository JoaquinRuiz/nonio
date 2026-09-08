"""SC-005 / Artículo I — ninguna cadena afirma autoría, en ningún sitio.

El test de esquema cubre la salida estructurada. Este cubre lo demás: mensajes
de error, textos de ayuda, render de terminal y documentación. Una herramienta
que no lo dice en el JSON pero sí en un mensaje de error sigue afirmando autoría.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

RAIZ = Path(__file__).resolve().parents[2]

# Afirmaciones de autoría. Se buscan como frase, no como palabra suelta: hablar
# *de* la autoría para negarla es exactamente lo que el proyecto debe hacer.
PROHIBIDAS = [
    re.compile(r"\bescrito por (una )?(IA|inteligencia artificial|máquina)\b", re.I),
    re.compile(r"\bwritten by (an? )?(AI|machine|human)\b", re.I),
    re.compile(r"\b(this|el|este) (text|texto) (is|es) (AI|IA)\b", re.I),
    re.compile(r"\bprobabilidad de (que sea|autoría)\b", re.I),
    re.compile(r"\bprobability (of|that).{0,20}(AI|human)-?(written|generated)\b", re.I),
    re.compile(r"\b\d+\s*% (AI|IA)\b", re.I),
]

# Frases que niegan, prohíben o citan a terceros: legítimas y necesarias. Negar
# una afirmación de autoría es justo lo que este proyecto tiene que hacer.
EXENTAS = re.compile(
    r"(no |not |never|nunca|jamás|ni que|sin |prohib|must not|cannot|no debe|"
    r"does not|doesn't|no existe|ninguna|existing detector|otros detector|"
    r"issues no verdict|misuse)",
    re.I,
)


def _fuentes():
    for patron in ("nonio/**/*.py", "docs/*.md", "README.md", "CONTRIBUTING.md"):
        yield from RAIZ.glob(patron)


def _parrafos(texto: str):
    """Agrupa líneas en párrafos.

    La unidad de análisis es el párrafo y no la línea porque la prosa va envuelta
    a 80 columnas: una negación puede quedar en la línea anterior a la frase que
    niega, y analizando por líneas se lee como afirmación lo que es su contrario.
    """
    buf: list[str] = []
    inicio = 1
    for i, linea in enumerate(texto.splitlines(), 1):
        if linea.strip():
            if not buf:
                inicio = i
            buf.append(linea)
        elif buf:
            yield inicio, " ".join(buf)
            buf = []
    if buf:
        yield inicio, " ".join(buf)


@pytest.mark.parametrize("regex", PROHIBIDAS, ids=lambda r: r.pattern[:32])
def test_ninguna_cadena_afirma_autoria(regex):
    ofensas = []
    for f in _fuentes():
        for n, parrafo in _parrafos(f.read_text(encoding="utf-8")):
            if regex.search(parrafo) and not EXENTAS.search(parrafo):
                ofensas.append(f"{f.relative_to(RAIZ)}:{n}: {parrafo.strip()[:110]}")
    assert not ofensas, "Artículo I — afirmación de autoría:\n" + "\n".join(ofensas)


def test_el_aviso_de_fr024_esta_en_el_render_y_en_el_readme():
    """FR-024: visible, no en una nota al pie."""
    from nonio.cli.render import AVISO

    assert "no debe ser base única" in AVISO
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert "must not be the sole basis" in readme


def test_el_readme_declara_el_desarrollo_asistido_por_ia():
    """FR-026 / Artículo X."""
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert "AI assistance" in readme and "specification-first" in readme
