"""Empaquetado del corpus para distribución (FR-022, SC-003, Artículo VII).

El corpus vive en el repositorio como ficheros sueltos —así se revisa por PR y se
ve el diff de cada texto— pero se **distribuye** como un solo `.jsonl.gz`.

El motivo es práctico y tiene consecuencia funcional: el corpus completo son
5.214 ficheros y 20 MB, de los que 4.251 pertenecen a una sola categoría de la
que la calibración usa 450. Meter eso en un wheel haría la instalación lenta y
pesada sin aportar nada. El paquete equilibrado son 1,2 MB en un fichero.

Que quepa importa: si el corpus no viaja con `pip install`, un tercero no puede
reproducir las cifras publicadas, y FR-022 dejaría de cumplirse para todo el que
no clone el repositorio.
"""

from __future__ import annotations

import gzip
import json
import random
from collections import Counter
from pathlib import Path

from nonio.calibration.corpus import CorpusCase, load_manifest
from nonio.schema.enums import CorpusCategory

__all__ = ["BUNDLE_NAME", "build_bundle", "load_bundle", "bundled_path"]

BUNDLE_NAME = "corpus.jsonl.gz"

#: Casos por categoría que viajan con el paquete. Coincide con el tope que usa la
#: calibración: distribuir más no cambiaría ninguna cifra.
BUNDLE_CAP = 450


def bundled_path() -> Path | None:
    """Ruta del corpus empaquetado dentro del paquete instalado, si existe."""
    p = Path(__file__).resolve().parent.parent / "_corpus" / BUNDLE_NAME
    return p if p.exists() else None


def build_bundle(
    manifest: Path, corpus_root: Path, out: Path, *, cap: int = BUNDLE_CAP, seed: int = 0
) -> dict[str, int]:
    """Construye el paquete equilibrado a partir del corpus del repositorio."""
    cases = load_manifest(manifest)
    random.Random(seed).shuffle(cases)

    seleccion: list[CorpusCase] = []
    cuenta: Counter[CorpusCategory] = Counter()
    for c in cases:
        if not c.redistributable or cuenta[c.category] >= cap:
            continue
        cuenta[c.category] += 1
        seleccion.append(c)
    seleccion.sort(key=lambda c: (c.category.value, c.id))

    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt", encoding="utf-8", compresslevel=9) as fh:
        for c in seleccion:
            fh.write(
                json.dumps(
                    {
                        "id": c.id,
                        "category": c.category.value,
                        "provenance": c.provenance,
                        "license": c.license,
                        "redistributable": c.redistributable,
                        "language": c.language,
                        "generator": c.generator,
                        "text": (corpus_root / c.text_path).read_text(encoding="utf-8"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return {k.value: v for k, v in cuenta.items()}


def load_bundle(path: Path | None = None) -> list[tuple[CorpusCase, str]]:
    """Carga el corpus empaquetado. Devuelve pares (caso, texto)."""
    p = path or bundled_path()
    if p is None or not p.exists():
        raise FileNotFoundError(
            "No se encontró el corpus empaquetado. Clona el repositorio para el "
            "corpus completo, o reinstala el paquete."
        )
    out: list[tuple[CorpusCase, str]] = []
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        for linea in fh:
            raw = json.loads(linea)
            texto = raw.pop("text")
            raw["category"] = CorpusCategory(raw["category"])
            raw["text_path"] = f"{raw['category'].value}/{raw['id']}.txt"
            out.append((CorpusCase(**raw), texto))
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Empaqueta el corpus para distribución")
    ap.add_argument("--manifest", type=Path, default=Path("corpus/manifest.jsonl"))
    ap.add_argument("--corpus", type=Path, default=Path("corpus/public"))
    ap.add_argument("--out", type=Path, default=Path("nonio/_corpus") / BUNDLE_NAME)
    ap.add_argument("--cap", type=int, default=BUNDLE_CAP)
    args = ap.parse_args(argv)

    cuenta = build_bundle(args.manifest, args.corpus, args.out, cap=args.cap)
    mb = args.out.stat().st_size / 1e6
    print(f"{args.out}  {mb:.1f} MB", file=sys.stderr)
    for k, v in sorted(cuenta.items()):
        print(f"  {k:24} {v}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
