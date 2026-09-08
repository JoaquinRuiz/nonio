"""Descarga de recursos de medición (FR-018, Artículo V).

**Único camino con red de todo el paquete.** Está separado de `analyze()` a
propósito: así el análisis nunca tiene motivo para conectarse y el Artículo V se
cumple por construcción, no por cuidado. Avisa de qué va a descargar y de dónde
antes de empezar.
"""

from __future__ import annotations

import sys

from nonio.backends.profiles import get_profile

__all__ = ["download_profile"]


def download_profile(profile_id: str, *, quiet: bool = False) -> dict[str, str]:
    from huggingface_hub import snapshot_download

    profile = get_profile(profile_id)
    if not quiet:
        print(
            f"Se van a descargar los recursos del perfil {profile.id!r} desde Hugging Face:\n"
            f"  observer:  {profile.observer_model}\n"
            f"  performer: {profile.performer_model}\n"
            "El texto que analices nunca sale de tu máquina; esto solo baja los modelos.",
            file=sys.stderr,
        )
    rutas = {}
    for papel, repo in (
        ("observer", profile.observer_model),
        ("performer", profile.performer_model),
    ):
        rutas[papel] = snapshot_download(
            repo,
            revision=profile.revision,
            allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"],
        )
    return rutas
