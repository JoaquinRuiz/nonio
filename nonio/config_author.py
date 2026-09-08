"""Enlaces del autor para el informe HTML.

Se configuran aparte del código de medición a propósito: son datos de quien
publica el proyecto, no del instrumento. El informe los muestra en un pie
claramente separado de la medida, nunca intercalados con las cifras.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["AuthorLinks", "load_author_links"]


@dataclass(frozen=True)
class AuthorLinks:
    name: str = ""
    tagline: str = ""
    youtube_url: str = ""
    youtube_label: str = ""
    books: tuple[dict[str, str], ...] = field(default_factory=tuple)
    site_url: str = ""

    @property
    def empty(self) -> bool:
        return not (self.youtube_url or self.books or self.site_url)


def load_author_links(path: Path | None = None) -> AuthorLinks:
    """Carga los enlaces desde `author.json` si existe; si no, devuelve vacío."""
    p = path or Path("author.json")
    if not p.exists():
        return AuthorLinks()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AuthorLinks()
    return AuthorLinks(
        name=raw.get("name", ""),
        tagline=raw.get("tagline", ""),
        youtube_url=raw.get("youtube_url", ""),
        youtube_label=raw.get("youtube_label", ""),
        books=tuple(raw.get("books", ())),
        site_url=raw.get("site_url", ""),
    )
