"""Configuración de usuario: recuerda el perfil elegido (FR-019)."""

from __future__ import annotations

import json
import os
from pathlib import Path

__all__ = ["config_path", "get_default_profile", "set_default_profile"]


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "nonio" / "config.json"


def _read() -> dict:
    p = config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_default_profile() -> str | None:
    return _read().get("default_profile")


def set_default_profile(profile_id: str) -> None:
    from nonio.backends.profiles import get_profile

    get_profile(profile_id)  # valida que existe antes de recordarlo
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = _read()
    data["default_profile"] = profile_id
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
