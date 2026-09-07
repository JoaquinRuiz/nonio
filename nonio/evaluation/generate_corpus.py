"""Generación de la categoría `generado` del corpus (T030, R-006).

**El generador nunca puede ser de la familia de un perfil de medición.** Si lo
fuera, ese perfil quedaría favorecido por construcción y las cifras publicadas
mentirían: el detector reconocería su propio modelo, no la generación automática
en general. La comprobación es dura y aborta, no avisa.

Modelo elegido: `ibm-granite/granite-3.1-2b-instruct`, Apache-2.0, familia IBM,
distinta de Qwen (perfil por defecto) y de BSC-LT (perfil de español). Se
descartó `projecte-aina/FLOR-1.3B` pese a ser Apache-2.0 y bueno en español
porque projecte-aina es del propio BSC, es decir, la misma familia que
Salamandra; y `bigscience/bloom` por su licencia RAIL, cuyas restricciones de uso
complicarían redistribuir sus salidas dentro de un corpus Apache-2.0.

Los prompts se guardan en la procedencia de cada caso: sin ellos, la categoría no
sería reproducible por un tercero (FR-022).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from nonio.backends.profiles import PROFILES
from nonio.calibration.corpus import CorpusCase, GeneratorConflictError, write_manifest
from nonio.schema.enums import CorpusCategory

GENERATOR = "ibm-granite/granite-3.1-2b-instruct"
GENERATOR_LICENSE = "Apache-2.0"

# Temas elegidos para cubrir registros distintos, no solo prosa expositiva:
# narrativa personal, opinión, descripción y exposición.
PROMPTS: tuple[str, ...] = (
    "Escribe un texto de unas 400 palabras contando un recuerdo de infancia en una casa de pueblo.",
    "Escribe unas 400 palabras describiendo una ciudad costera en invierno.",
    "Escribe unas 400 palabras de opinión sobre por qué leer novelas largas merece la pena.",
    "Escribe unas 400 palabras explicando cómo funciona el sistema de riego de un huerto pequeño.",
    "Escribe unas 400 palabras narrando un viaje en tren que se retrasa varias horas.",
    "Escribe unas 400 palabras sobre las diferencias entre el café de puchero y el italiano.",
    "Escribe unas 400 palabras describiendo el oficio de un encuadernador artesano.",
    "Escribe unas 400 palabras sobre la experiencia de aprender un idioma de adulto.",
    "Escribe unas 400 palabras narrando una mudanza a otra ciudad.",
    "Escribe unas 400 palabras sobre por qué las plazas de barrio importan en una ciudad.",
)


def _assert_generator_is_foreign(generator: str) -> None:
    """R-006: aborta si el generador comparte familia con un perfil de medición."""
    familias = {p.observer_model.split("/")[0].lower() for p in PROFILES.values()}
    if generator.split("/")[0].lower() in familias:
        raise GeneratorConflictError(
            f"{generator!r} pertenece a la familia de un perfil de medición "
            f"({sorted(familias)}). Generar el corpus con él inflaría las cifras "
            "por construcción (R-006)."
        )


def generate(
    out_root: Path, *, n_per_prompt: int = 4, max_new_tokens: int = 600, seed: int = 0
) -> list[CorpusCase]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    _assert_generator_is_foreign(GENERATOR)

    tok = AutoTokenizer.from_pretrained(GENERATOR, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        GENERATOR, dtype=torch.float32, local_files_only=True
    ).eval()

    out_dir = out_root / CorpusCategory.GENERADO.value
    out_dir.mkdir(parents=True, exist_ok=True)
    cases: list[CorpusCase] = []

    for pi, prompt in enumerate(PROMPTS):
        for k in range(n_per_prompt):
            torch.manual_seed(seed + pi * 100 + k)
            chat = tok.apply_chat_template(
                [{"role": "user", "content": prompt}],
                add_generation_prompt=True,
                tokenize=False,
            )
            ids = tok(chat, return_tensors="pt")
            with torch.no_grad():
                out = model.generate(
                    **ids,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=0.9,
                    top_p=0.95,
                    pad_token_id=tok.eos_token_id,
                )
            text = tok.decode(out[0][ids["input_ids"].shape[1] :], skip_special_tokens=True).strip()
            if len(text.split()) < 150:
                continue

            cid = f"gen-{hashlib.sha1(text.encode()).hexdigest()[:10]}"
            rel = f"{CorpusCategory.GENERADO.value}/{cid}.txt"
            (out_root / rel).write_text(text + "\n", encoding="utf-8")
            cases.append(
                CorpusCase(
                    id=cid,
                    category=CorpusCategory.GENERADO,
                    text_path=rel,
                    provenance=(
                        f"Generado con {GENERATOR} (temp=0.9, top_p=0.95, "
                        f"seed={seed + pi * 100 + k}); prompt: {prompt!r}"
                    ),
                    license=GENERATOR_LICENSE,
                    redistributable=True,
                    language="es",
                    generator=GENERATOR,
                )
            )
            print(f"  {cid}  {len(text.split())} palabras", file=sys.stderr)
    return cases


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Genera la categoría `generado` del corpus")
    ap.add_argument("--out", type=Path, default=Path("corpus/public"))
    ap.add_argument("--manifest", type=Path, default=Path("corpus/manifest.jsonl"))
    ap.add_argument("--n-per-prompt", type=int, default=4)
    args = ap.parse_args(argv)

    cases = generate(args.out, n_per_prompt=args.n_per_prompt)
    if args.manifest.exists():
        from nonio.calibration.corpus import load_manifest

        previos = {c.id: c for c in load_manifest(args.manifest)}
        previos.update({c.id: c for c in cases})
        cases = list(previos.values())
    write_manifest(args.manifest, cases)
    print(f"generado: {len(cases)} casos en total", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
