"""Identificación local de idioma (FR-007, FR-016, Artículo V).

Es parte del camino crítico de corrección, no un adorno: el Artículo VIII
prohíbe extrapolar umbrales entre idiomas, así que equivocarse de idioma
significa aplicar una calibración que no corresponde. Sin red, siempre.

Se usa el identificador con `norm_probs=True` porque `py3langid.classify()` a
secas devuelve una log-probabilidad cruda (negativa y sin cota), no una
confianza. Compararla con un umbral entre 0 y 1 rechaza textos correctos y
acepta ruido: un "Hola." suelto puntúa +2.85 y se colaría como hausa, mientras
que un párrafo en español legítimo puntúa -783 y se descartaría.
"""

from __future__ import annotations

from functools import lru_cache

from py3langid.langid import MODEL_FILE, LanguageIdentifier

__all__ = ["detect_language"]

# Por debajo de esta confianza no se afirma el idioma: se devuelve None y el
# resultado acaba en abstención por idioma, preferible a acertar por azar.
_MIN_CONFIDENCE = 0.5
_MIN_WORDS = 5

# Códigos que significan "esto no es lengua": `zxx` es el ISO 639-2 para
# ausencia de contenido lingüístico y `und` para indeterminado. Ninguno es un
# idioma para el que pueda existir calibración, así que ambos llevan a
# abstención por idioma (FR-007) en vez de tratarse como lengua detectada.
_NOT_A_LANGUAGE = {"zxx", "und"}


@lru_cache(maxsize=1)
def _identifier() -> LanguageIdentifier:
    return LanguageIdentifier.from_model_file(MODEL_FILE, norm_probs=True)


def detect_language(text: str) -> str | None:
    """Devuelve el código ISO 639-1, o `None` si no hay confianza suficiente."""
    stripped = text.strip()
    if len(stripped.split()) < _MIN_WORDS:
        return None
    lang, confidence = _identifier().classify(stripped)
    if confidence < _MIN_CONFIDENCE or lang in _NOT_A_LANGUAGE:
        return None
    return lang
