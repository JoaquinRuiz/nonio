"""Carga y verificación de los recursos de medición (FR-018, FR-021, Artículo V).

`analyze()` nunca sale a red. Si falta un modelo, falla con
`ResourceUnavailableError` diciendo cómo obtenerlo, en vez de descargarlo en
silencio: el texto que el usuario analiza es sensible y la descarga es un gesto
que le corresponde a él (`nonio download`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from nonio.backends.profiles import Profile, get_profile

__all__ = [
    "LoadedPair",
    "ResourceUnavailableError",
    "ProfileMismatchError",
    "check_resources",
    "load_pair",
]


class ResourceUnavailableError(RuntimeError):
    """Falta un recurso de medición o está corrupto. Condición de entorno."""


class ProfileMismatchError(RuntimeError):
    """Se intentó aplicar la calibración de un perfil a otro (R-003)."""


@dataclass(frozen=True)
class LoadedPair:
    profile: Profile
    tokenizer: object
    observer: object
    performer: object


def _offline_env() -> dict[str, str]:
    """Fuerza el modo sin red de huggingface durante el análisis."""
    return {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}


def check_resources(profile_id: str | None = None) -> dict[str, object]:
    """Comprueba disponibilidad local sin salir a red (FR-018).

    Equivale al comando `nonio check`.
    """
    from huggingface_hub import try_to_load_from_cache

    profile = get_profile(profile_id)
    estado: dict[str, object] = {"profile": profile.id, "models": {}, "available": True}
    for papel, repo in (
        ("observer", profile.observer_model),
        ("performer", profile.performer_model),
    ):
        hit = try_to_load_from_cache(repo, "config.json", revision=profile.revision)
        presente = isinstance(hit, str)
        estado["models"][papel] = {  # type: ignore[index]
            "repo": repo,
            "present": presente,
            "hint": None if presente else f"nonio download {profile.id}",
        }
        if not presente:
            estado["available"] = False
    return estado


@lru_cache(maxsize=2)
def load_pair(profile_id: str | None = None) -> LoadedPair:
    """Carga el par observer/performer desde la caché local. Nunca descarga."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    profile = get_profile(profile_id)
    previo = {k: os.environ.get(k) for k in _offline_env()}
    os.environ.update(_offline_env())
    try:
        common = {"revision": profile.revision, "local_files_only": True}
        tokenizer = AutoTokenizer.from_pretrained(profile.observer_model, **common)
        observer = AutoModelForCausalLM.from_pretrained(
            profile.observer_model, dtype=torch.float32, **common
        ).eval()
        performer = AutoModelForCausalLM.from_pretrained(
            profile.performer_model, dtype=torch.float32, **common
        ).eval()
    except Exception as exc:  # noqa: BLE001
        raise ResourceUnavailableError(
            f"No se pudo cargar el perfil {profile.id!r} desde la caché local. "
            f"Obtén los recursos con: nonio download {profile.id}\n  causa: {exc}"
        ) from exc
    finally:
        for k, v in previo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    tok_o = tokenizer.__class__.__name__
    tok_p = AutoTokenizer.from_pretrained(
        profile.performer_model, revision=profile.revision, local_files_only=True
    )
    if tok_p.get_vocab() != tokenizer.get_vocab():
        raise ProfileMismatchError(
            f"El par de {profile.id!r} no comparte tokenizador ({tok_o}); "
            "Binoculars exige modelos hermanos con vocabulario común."
        )
    return LoadedPair(profile=profile, tokenizer=tokenizer, observer=observer, performer=performer)
