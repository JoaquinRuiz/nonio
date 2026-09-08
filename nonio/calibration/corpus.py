"""Corpus de evaluación (FR-020, FR-029, Artículo VII).

Cada caso lleva su licencia y su procedencia porque el corpus público es de
licencia mixta: dominio público, Apache-2.0 y CC BY-SA conviven, y share-alike y
atribución tienen obligaciones distintas (R-006).

Dos invariantes que no son burocracia:

- Un caso de categoría `generado` **no puede** haberse producido con un modelo de
  la familia de un perfil de medición activo. Si lo fuera, ese perfil quedaría
  favorecido por construcción y las cifras publicadas mentirían.
- `redistributable` separa el corpus público del privado. Las cifras del privado
  se publican marcadas como no reproducibles por terceros (SC-003).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from nonio.schema.enums import CorpusCategory

__all__ = ["CorpusCase", "load_manifest", "write_manifest", "GeneratorConflictError"]


class GeneratorConflictError(RuntimeError):
    """Un caso generado usa la familia de un perfil de medición (R-006)."""


@dataclass(frozen=True)
class CorpusCase:
    id: str
    category: CorpusCategory
    text_path: str
    provenance: str
    license: str
    redistributable: bool
    language: str = "es"
    generator: str | None = None

    def read_text(self, root: Path) -> str:
        return (root / self.text_path).read_text(encoding="utf-8")

    def validate_against_profiles(self, profile_families: set[str]) -> None:
        if self.category is not CorpusCategory.GENERADO:
            return
        if not self.generator:
            raise ValueError(f"{self.id}: un caso generado debe declarar su generador")
        family = self.generator.split("/")[0].lower()
        if family in {f.lower() for f in profile_families}:
            raise GeneratorConflictError(
                f"{self.id}: generado con {self.generator!r}, de la misma familia que un perfil "
                "de medición. Las cifras quedarían infladas por construcción (R-006)."
            )


def load_manifest(path: Path) -> list[CorpusCase]:
    cases: list[CorpusCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        raw = json.loads(line)
        raw["category"] = CorpusCategory(raw["category"])
        cases.append(CorpusCase(**raw))
    return cases


def write_manifest(path: Path, cases: list[CorpusCase]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for case in sorted(cases, key=lambda c: (c.category.value, c.id)):
            row = asdict(case)
            row["category"] = case.category.value
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
