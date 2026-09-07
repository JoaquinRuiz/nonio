"""Ensamblado del corpus público (FR-020, FR-029, Artículo VII).

Reproducible por terceros: cada categoría se construye desde una fuente
redistribuible declarada, y el manifiesto registra licencia y procedencia caso a
caso porque el corpus es de licencia mixta (R-006).

Fuentes por categoría:

| Categoría              | Fuente                                  | Licencia   |
|------------------------|-----------------------------------------|------------|
| espanol_no_nativo      | COWS-L2H (UC Davis)                     | Apache-2.0 |
| humano_pre2022         | Project Gutenberg / Wikisource          | Dominio púb|
| tecnica_estructurada   | Documentación técnica con licencia libre| CC BY-SA   |
| generado               | Generado por el proyecto                | Apache-2.0 |
| mixto                  | Editado por personas sobre salida de    | Apache-2.0 |
|                        | modelo, con protocolo documentado       |            |

**Sobre `espanol_no_nativo`:** se filtran los casos cuya L1 declarada incluye
español. Un hablante de herencia no es un hablante no nativo, y mezclarlos
difumina justo la categoría que el Artículo III obliga a medir por separado.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import sys
from pathlib import Path

from nonio.calibration.corpus import CorpusCase, write_manifest
from nonio.evaluation.sources_wikipedia import (
    LICENSE as WIKI_LICENSE,
)
from nonio.evaluation.sources_wikipedia import (
    fetch_category_members,
    fetch_pre2022_text,
)
from nonio.schema.enums import CorpusCategory

__all__ = ["build_non_native_from_cowsl2h", "build_from_wikipedia"]

# Categorías de Wikipedia por registro. La separación es deliberada: la prosa
# expositiva muy estructurada es justo la que el Artículo III señala como
# propensa a falsos positivos, y medirla mezclada con narrativa la escondería.
WIKI_SOURCES: dict[CorpusCategory, tuple[str, ...]] = {
    CorpusCategory.HUMANO_PRE2022: (
        "Historia de España",
        "Escritores de España",
        "Ciudades de España",
        "Pintores de España",
    ),
    CorpusCategory.TECNICA_ESTRUCTURADA: (
        "Álgebra",
        "Termodinámica",
        "Estructuras de datos",
        "Protocolos de red",
    ),
}

# Los textos se trocean para que cada caso sea comparable en longitud con una
# redacción de estudiante; medir un artículo de 9.000 palabras contra una de 250
# compararía longitudes, no señales.
CHUNK_WORDS = 400

COWSL2H_URL = "https://github.com/ucdaviscl/cowsl2h"
COWSL2H_LICENSE = "Apache-2.0"

# Longitud mínima con la que se admite un caso en el corpus. NO es el mínimo
# calibrado del sistema: ese lo fija la medición (T032). Aquí solo se descartan
# textos demasiado cortos para ser útiles en ninguna configuración.
CORPUS_MIN_WORDS = 150


def _case_id(prefix: str, text: str) -> str:
    return f"{prefix}-{hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]}"


def build_non_native_from_cowsl2h(
    cowsl2h_root: Path, out_root: Path, *, min_words: int = CORPUS_MIN_WORDS
) -> list[CorpusCase]:
    """Extrae redacciones de estudiantes cuya L1 declarada no incluye español."""
    out_dir = out_root / "espanol_no_nativo"
    out_dir.mkdir(parents=True, exist_ok=True)
    cases: list[CorpusCase] = []
    vistos: set[str] = set()

    for path in sorted(glob.glob(str(cowsl2h_root / "csv" / "*.csv"))):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh):
                essay = (row.get("essay") or "").strip()
                l1 = (row.get("l1 language") or "").strip().lower()
                if not essay or not l1:
                    continue
                # Hablante de herencia no es hablante no nativo.
                if "spanish" in l1 or "español" in l1:
                    continue
                if len(essay.split()) < min_words:
                    continue
                digest = hashlib.sha1(essay.encode("utf-8")).hexdigest()
                if digest in vistos:
                    continue
                vistos.add(digest)

                cid = _case_id("nn", essay)
                rel = f"espanol_no_nativo/{cid}.txt"
                (out_root / rel).write_text(essay + "\n", encoding="utf-8")
                cases.append(
                    CorpusCase(
                        id=cid,
                        category=CorpusCategory.ESPANOL_NO_NATIVO,
                        text_path=rel,
                        provenance=(
                            f"COWS-L2H {Path(path).name}, L1={l1!r}, prompt="
                            f"{row.get('prompt', '?')!r} — {COWSL2H_URL}"
                        ),
                        license=COWSL2H_LICENSE,
                        redistributable=True,
                        language="es",
                    )
                )
    return cases


def _chunks(text: str, size: int = CHUNK_WORDS) -> list[str]:
    """Trocea por párrafos completos hasta alcanzar `size` palabras."""
    out, buf, n = [], [], 0
    for para in text.split("\n\n"):
        w = len(para.split())
        if not w:
            continue
        buf.append(para)
        n += w
        if n >= size:
            out.append("\n\n".join(buf))
            buf, n = [], 0
    if n >= CORPUS_MIN_WORDS:
        out.append("\n\n".join(buf))
    return out


def build_from_wikipedia(
    out_root: Path, *, per_category: int = 40, min_words: int = CORPUS_MIN_WORDS
) -> list[CorpusCase]:
    """Extrae texto humano anterior a 2022, separado por registro."""
    cases: list[CorpusCase] = []
    for category, cats in WIKI_SOURCES.items():
        out_dir = out_root / category.value
        out_dir.mkdir(parents=True, exist_ok=True)
        hechos = 0
        for cat in cats:
            if hechos >= per_category:
                break
            for title in fetch_category_members(cat, limit=25):
                if hechos >= per_category:
                    break
                try:
                    wiki = fetch_pre2022_text(title)
                except Exception as exc:  # noqa: BLE001
                    print(f"  aviso: {title}: {exc}", file=sys.stderr)
                    continue
                if not wiki:
                    continue
                for chunk in _chunks(wiki.text):
                    if len(chunk.split()) < min_words or hechos >= per_category:
                        continue
                    cid = _case_id(category.value[:3], chunk)
                    rel = f"{category.value}/{cid}.txt"
                    (out_root / rel).write_text(chunk + "\n", encoding="utf-8")
                    cases.append(
                        CorpusCase(
                            id=cid,
                            category=category,
                            text_path=rel,
                            provenance=wiki.provenance,
                            license=WIKI_LICENSE,
                            redistributable=True,
                            language="es",
                        )
                    )
                    hechos += 1
        print(f"{category.value}: {hechos} casos", file=sys.stderr)
    return cases


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ensambla el corpus público de Nonio")
    ap.add_argument("--cowsl2h", type=Path, help="Ruta a un clon de ucdaviscl/cowsl2h")
    ap.add_argument("--out", type=Path, default=Path("corpus/public"))
    ap.add_argument("--manifest", type=Path, default=Path("corpus/manifest.jsonl"))
    ap.add_argument("--min-words", type=int, default=CORPUS_MIN_WORDS)
    ap.add_argument("--wikipedia", action="store_true", help="Descarga texto pre-2022")
    ap.add_argument("--per-category", type=int, default=40)
    args = ap.parse_args(argv)

    cases: list[CorpusCase] = []
    if args.cowsl2h:
        cases += build_non_native_from_cowsl2h(args.cowsl2h, args.out, min_words=args.min_words)
        print(f"espanol_no_nativo: {len(cases)} casos", file=sys.stderr)

    if args.wikipedia:
        cases += build_from_wikipedia(
            args.out, per_category=args.per_category, min_words=args.min_words
        )

    # Se conserva lo ya presente en el manifiesto para poder construir por partes.
    if args.manifest.exists():
        from nonio.calibration.corpus import load_manifest

        previos = {c.id: c for c in load_manifest(args.manifest)}
        previos.update({c.id: c for c in cases})
        cases = list(previos.values())

    if cases:
        write_manifest(args.manifest, cases)
        print(f"manifiesto: {args.manifest} ({len(cases)} casos)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
