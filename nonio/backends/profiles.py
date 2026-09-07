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
    ),
    "salamandra-2b": Profile(
        id="salamandra-2b",
        observer_model="BSC-LT/salamandra-2b",
        performer_model="BSC-LT/salamandra-2b-instruct",
        revision="main",
        validated_languages=(),
        note=(
            "Español primero (BSC). Apache-2.0. Mejor calidad esperada en español, "
            "más coste; puede no cumplir SC-006 en CPU modesta."
        ),
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
