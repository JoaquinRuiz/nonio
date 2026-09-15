"""Perfiles de medición: pares de modelos hermanos (FR-019, R-003).

Binoculars exige dos modelos estrechamente emparentados y de rendimiento
similar; base + instruct de la misma familia es exactamente ese caso, y comparten
tokenizador, lo que hace la cross-perplexity calculable sin realineamiento.

**Los umbrales pertenecen al perfil.** Un umbral calibrado sobre `qwen2.5-0.5b`
no es válido sobre `salamandra-2b`. Aplicar el de uno al otro sería el mismo
error que el Artículo VIII prohíbe entre idiomas, y el cargador lo rechaza.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["Profile", "PROFILES", "DEFAULT_PROFILE_ID", "get_profile", "profiles"]

DEFAULT_PROFILE_ID = "qwen2.5-0.5b"


@dataclass(frozen=True)
class Profile:
    id: str
    observer_model: str
    performer_model: str
    revision: str
    validated_languages: tuple[str, ...]
    note: str
    #: Precisión con la que se cargan los pesos.
    #:
    #: Medido en Apple Silicon (CPU), pasada de 400 tokens sobre salamandra-2b:
    #:
    #:   float32    0.92 s   18 GB el par
    #:   float16    5.59 s    9 GB el par
    #:   bfloat16   8.77 s    9 GB el par
    #:
    #: Reducir la precisión ahorra la mitad de memoria y cuesta entre 6 y 9 veces
    #: más tiempo: PyTorch en esta CPU no tiene kernels optimizados para media
    #: precisión y cae a una ruta lenta. Así que la elección no es memoria contra
    #: precisión sino memoria contra horas, y por eso los perfiles grandes
    #: declaran cuánta RAM piden en vez de encogerse para caber.
    #:
    #: Bajar la precisión no rompería FR-006 —el determinismo es reproducibilidad
    #: en la misma máquina, no precisión absoluta— pero sí haría incomparables dos
    #: perfiles medidos en regímenes numéricos distintos.
    dtype: str = "float32"
    # Mediana y p95 medidos en el hardware de referencia (SC-006). `None` hasta
    # que T069 los mida: no se inventan.
    measured_runtime: dict[str, float] | None = field(default=None)


PROFILES: dict[str, Profile] = {
    "qwen2.5-0.5b": Profile(
        id="qwen2.5-0.5b",
        observer_model="Qwen/Qwen2.5-0.5B",
        performer_model="Qwen/Qwen2.5-0.5B-Instruct",
        revision="main",
        validated_languages=(),  # vacío hasta que la calibración lo demuestre
        note="Perfil por defecto. Apache-2.0. Rápido en CPU; cumple SC-006 con margen.",
        dtype="float32",
        # Medido (SC-006): 1.000 palabras, Apple Silicon, CPU, float32. El p95 se
        # tomó con otra carga compitiendo por CPU, así que es un peor caso realista.
        measured_runtime={"words": 1000, "median_s": 12.1, "p95_s": 19.1},
    ),
    "salamandra-2b": Profile(
        id="salamandra-2b",
        observer_model="BSC-LT/salamandra-2b",
        performer_model="BSC-LT/salamandra-2b-instruct",
        revision="main",
        validated_languages=(),
        note=(
            "Español primero (BSC). Apache-2.0. Medido: 34,2 s de mediana para "
            "1.000 palabras en CPU, por encima del presupuesto de 30 s de SC-006. "
            "Úsalo si prefieres calidad a interactividad. Necesita ~19 GB de RAM: "
            "en float16 cabría en la mitad pero tarda 6 veces más en CPU."
        ),
        dtype="float32",
        # Medido (SC-006): 1.000 palabras, Apple Silicon, CPU, float32.
        # NO cumple el presupuesto de 30 s. Se declara en vez de ocultarse: el
        # perfil sigue disponible porque el coste es una elección informada del
        # usuario, no un defecto que haya que esconder.
        measured_runtime={"words": 1000, "median_s": 34.2, "p95_s": 98.2},
    ),
}


def profiles() -> list[Profile]:
    """Lista los perfiles conocidos. Equivale a `nonio profiles`."""
    return list(PROFILES.values())


def get_profile(profile_id: str | None = None) -> Profile:
    pid = profile_id or DEFAULT_PROFILE_ID
    if pid not in PROFILES:
        raise KeyError(f"Perfil desconocido: {pid!r}. Disponibles: {sorted(PROFILES)}")
    return PROFILES[pid]
