"""Render legible en terminal (FR-024, FR-003, SC-008).

Encabezado por el aviso del Artículo IX: quien lea el resultado en la terminal
debe verlo antes que la cifra, no en una nota al pie que se pierde al copiar.

Muestra el valor **individual de cada señal** además de la lectura combinada
(FR-003) y el porcentaje excluido (SC-008): sin ellos el usuario no puede
discutir el resultado, que es justo lo que la historia principal pide.
"""

from __future__ import annotations

from nonio.schema.models import Abstention, AnalysisResult, Reading

__all__ = ["render"]

AVISO = (
    "Nonio no decide autoría. Esta salida no debe ser base única de ninguna "
    "decisión académica, laboral o editorial."
)


def _señales(signals) -> list[str]:
    filas = ["  señales:"]
    for s in sorted(signals, key=lambda x: x.name):
        norm = "n/d" if s.normalized_value != s.normalized_value else f"{s.normalized_value:.3f}"
        filas.append(
            f"    {s.name:<18} valor={s.raw_value:+9.4f}   percentil={norm}   "
            f"rango esperado=[{s.expected_range[0]:g}, {s.expected_range[1]:g}]"
        )
    return filas


def _repro(flag: bool) -> str:
    return "sí (corpus público)" if flag else "no (corpus privado)"


def render(result: AnalysisResult) -> str:
    d = result.document
    out = [
        f"⚠  {AVISO}",
        "",
        f"fuente: {d.source}",
        f"perfil: {result.profile.id}   idioma detectado: {d.detected_language or 'n/d'}",
        f"palabras medibles: {d.measurable_word_count}   "
        f"excluido del cálculo: {d.excluded_ratio:.1%}",
        "",
    ]

    r = result.result
    if isinstance(r, Abstention):
        out += [
            f"RESULTADO: insufficient_evidence  ({r.cause.value})",
            f"  {r.detail}",
        ]
        if r.signals:
            out += _señales(r.signals)
        out += [
            "",
            "  La abstención es un resultado completo, no un fallo: Nonio no arriesga una",
            "  medida que no se sostiene.",
        ]
        return "\n".join(out)

    assert isinstance(r, Reading)
    out += [
        f"RESULTADO: señal {r.level.value.upper()}",
        f"  umbral aplicado:     {r.applied_threshold:.4f}",
        f"  falsos positivos:    {r.measured_fpr:.1%}  medidos sobre «{r.fpr_category.value}»",
        f"  cifra reproducible:  {_repro(r.fpr_reproducible)}",
    ]
    out += _señales(r.signals)

    if r.top_spans:
        out += ["", "  tramos que más contribuyen:"]
        for s in r.top_spans:
            out.append(
                f"    caracteres {s.start}–{s.end}"
                + (f"   contribución={s.contribution:.2f}" if s.contribution is not None else "")
            )

    if result.blocks:
        out += ["", f"  desglose por bloque ({len(result.blocks)}):"]
        for b in result.blocks:
            if isinstance(b.result, Reading):
                estado = f"señal {b.result.level.value}"
            else:
                estado = f"insufficient_evidence ({b.result.cause.value})"
            out.append(f"    [{b.index}] {b.start:>6}–{b.end:<6} {b.token_count:>4} tok  {estado}")

    out += [
        "",
        "  El nivel describe la intensidad de una señal estadística, no quién escribió el texto.",
    ]
    return "\n".join(out)
