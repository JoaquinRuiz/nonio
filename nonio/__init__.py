"""Nonio — instrumento de medida de señales de generación automática en texto.

No decide autoría. Toda salida es una medida con su margen.

La superficie pública es esta y solo esta; lo que no aparece aquí es interno y
puede cambiar sin aviso (Artículo VI). Cada capacidad de la CLI tiene su
equivalente importable: `nonio analyze` -> `analyze()`, `nonio eval` ->
`evaluate()`, y así con el resto.
"""

from __future__ import annotations

from nonio.backends.loader import (
    ProfileMismatchError,
    ResourceUnavailableError,
    check_resources,
)
from nonio.backends.profiles import Profile, profiles
from nonio.backends.profiles import get_profile as load_profile
from nonio.core import NONIO_VERSION, UnreadableInputError, analyze
from nonio.schema.enums import AbstentionCause, CorpusCategory, Level
from nonio.schema.export import SCHEMA_VERSION, output_schema
from nonio.schema.models import Abstention, AnalysisResult, Block, Reading, Signal

__version__ = NONIO_VERSION

__all__ = [
    # análisis
    "analyze",
    # resultados
    "AnalysisResult",
    "Reading",
    "Abstention",
    "Block",
    "Signal",
    "Level",
    "AbstentionCause",
    "CorpusCategory",
    # recursos de medición
    "profiles",
    "load_profile",
    "check_resources",
    "Profile",
    # contrato
    "output_schema",
    "SCHEMA_VERSION",
    "__version__",
    # errores de entorno (nunca de propiedades del texto)
    "ResourceUnavailableError",
    "ProfileMismatchError",
    "UnreadableInputError",
]


def evaluate(**kwargs):
    """Ejecuta la evaluación sobre el corpus. Equivale a `nonio eval`.

    Importa perezosamente porque arrastra el corpus y los modelos, y `analyze()`
    no debe pagar ese coste.
    """
    from nonio.evaluation.harness import evaluate as _evaluate

    return _evaluate(**kwargs)


def download_profile(profile_id: str, **kwargs):
    """Descarga los recursos de un perfil. Equivale a `nonio download`.

    **Único punto de la API que usa la red** (Artículo V).
    """
    from nonio.backends.download import download_profile as _download

    return _download(profile_id, **kwargs)


def set_default_profile(profile_id: str) -> None:
    """Recuerda el perfil elegido. Equivale a `nonio profiles use` (FR-019)."""
    from nonio.config import set_default_profile as _set

    _set(profile_id)


__all__ += ["evaluate", "download_profile", "set_default_profile"]
