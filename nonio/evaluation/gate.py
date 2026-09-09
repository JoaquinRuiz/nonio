"""Comprobación de la puerta de sesgo sobre un artefacto de calibración (FR-030).

Lee un informe de calibración ya medido y guardado, así que **no necesita
modelos ni corpus**: puede ejecutarse en integración continua en segundos. Medir
de nuevo en cada push costaría descargar 1 GB y una hora de CPU sin cambiar nada.

Semántica de los códigos de salida, que no es la obvia:

- `pasa` → 0
- `no_concluyente` → 0 **con aviso**. Es el estado real del proyecto hoy y está
  registrado en el roadmap; dejar la integración continua en rojo de forma
  permanente convertiría el rojo en ruido y nadie miraría el siguiente.
- `bloquea` → 1. Aquí sí: significa que se ha demostrado que el umbral es
  demasiado injusto para publicarse.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

__all__ = ["check_artifact"]

DEFAULT_ARTIFACT = Path("calibration/qwen2.5-0.5b-es.json")


def check_artifact(path: Path, *, max_ratio: float = 2.0) -> tuple[int, str]:
    """Devuelve (código de salida, mensaje) para el artefacto dado."""
    if not path.exists():
        return 1, f"No existe el artefacto de calibración: {path}"

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return 1, f"{path} no es JSON válido: {exc}"

    bias = data.get("bias") or {}
    ratio = bias.get("ratio_non_native_vs_general")
    ci = bias.get("ci95")
    verdict = bias.get("verdict")
    absoluta = bias.get("absolute_fpr_general")

    if ratio is None:
        return 1, "El artefacto no declara cociente de sesgo (FR-030)."
    if ci is None:
        # FR-031: una cifra de sesgo sin intervalo no es una medida.
        return 1, "El artefacto declara un cociente sin intervalo de confianza (FR-031)."

    detalle = f"sesgo {ratio:.2f}× IC95% [{ci[0]:.2f}, {ci[1]:.2f}] (máximo {max_ratio:.1f}×)"
    if absoluta is not None:
        detalle += f"; FP absoluta sobre texto humano general {absoluta:.1%}"

    faltan = data.get("missing_categories") or []
    if faltan:
        detalle += f"; categorías ausentes: {', '.join(faltan)}"

    if verdict == "bloquea":
        return 1, f"FR-030 BLOQUEA la publicación — {detalle}"
    if verdict == "no_concluyente":
        return 0, (
            f"FR-030 NO CONCLUYENTE — {detalle}.\n"
            "El intervalo cruza el límite: hace falta más muestra para decidir. "
            "No habilita publicar umbral por defecto. Seguimiento: issue #3."
        )
    if verdict == "pasa":
        return 0, f"FR-030 pasa — {detalle}"
    return 1, f"Veredicto desconocido {verdict!r}; no se puede comprobar la puerta."


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Comprueba la puerta de sesgo de FR-030")
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--max-ratio", type=float, default=2.0)
    args = ap.parse_args(argv)

    codigo, mensaje = check_artifact(args.artifact, max_ratio=args.max_ratio)
    print(mensaje, file=sys.stderr if codigo else sys.stdout)
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
