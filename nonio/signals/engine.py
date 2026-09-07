"""Motor de medición: una sola pasada por modelo (R-007).

Es lo que hace compatibles FR-004 (medida por bloque) y SC-006 (presupuesto de
tiempo) a la vez.

- **Memoria.** La cross-perplexity de Binoculars necesita las distribuciones
  completas de ambos modelos en cada posición. Guardarlas para 1.500 tokens con
  un vocabulario de ~150.000 entradas serían unos 900 MB en float32. Calculando
  la señal por token y quedándose solo con el escalar, la memoria queda acotada
  por el tamaño del trozo, no por la longitud del documento.
- **Tiempo.** Medir cada bloque por separado repetiría el prefijo del documento
  en cada pasada. Una sola pasada con acumuladores por bloque da el agregado y el
  desglose al mismo coste.

**Consecuencia documentada:** cada bloque se mide *en el contexto del documento*,
no aislado. Es lo correcto para texto mixto —el escenario 3 de la spec— pero
significa que la medida de un bloque no es idéntica a la que daría suelto.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from nonio.backends.loader import LoadedPair
from nonio.signals.base import SignalOutput
from nonio.signals.binoculars import Binoculars
from nonio.signals.fast_detect_gpt import FastDetectGPT

__all__ = ["Measurement", "TokenSpan", "measure", "SCORERS"]

SCORERS = (FastDetectGPT(), Binoculars())

# Ventana con solapamiento para documentos que exceden el contexto del modelo.
_WINDOW = 1024
_STRIDE = 896


@dataclass(frozen=True)
class TokenSpan:
    """Correspondencia entre un tramo de caracteres y sus posiciones de token."""

    char_start: int
    char_end: int
    tok_start: int
    tok_end: int


@dataclass(frozen=True)
class Measurement:
    signals: dict[str, SignalOutput]
    offsets: list[tuple[int, int]]
    n_tokens: int

    def token_range(self, char_start: int, char_end: int) -> tuple[int, int]:
        """Posiciones de token que caen dentro de [char_start, char_end)."""
        lo = hi = None
        for i, (s, e) in enumerate(self.offsets):
            if e <= char_start or s >= char_end:
                continue
            if lo is None:
                lo = i
            hi = i + 1
        return (lo or 0, hi or 0)

    def aggregate(self, char_start: int, char_end: int) -> dict[str, float]:
        lo, hi = self.token_range(char_start, char_end)
        # Las señales viven sobre pares (t, t+1), de ahí el desplazamiento.
        return {
            name: sig.aggregate(max(0, lo - 1), max(0, hi - 1))
            for name, sig in self.signals.items()
        }


def measure(text: str, pair: LoadedPair) -> Measurement:
    """Mide el texto completo en una pasada por modelo."""
    enc = pair.tokenizer(text, return_offsets_mapping=True, return_tensors="pt", truncation=False)
    ids = enc["input_ids"][0]
    offsets = [tuple(o) for o in enc["offset_mapping"][0].tolist()]
    n = ids.shape[0]

    if n < 2:
        empty = torch.empty(0)
        return Measurement(
            signals={s.name: SignalOutput(s.name, empty, s.expected_range) for s in SCORERS},
            offsets=offsets,
            n_tokens=n,
        )

    per_token: dict[str, torch.Tensor] = {
        s.name: torch.full((n - 1,), float("nan")) for s in SCORERS
    }

    with torch.no_grad():
        for start in range(0, n, _STRIDE):
            chunk = ids[start : start + _WINDOW]
            if chunk.shape[0] < 2:
                break
            batch = chunk.unsqueeze(0)
            obs_logits = pair.observer(batch).logits[0]
            per_logits = pair.performer(batch).logits[0]

            for scorer in SCORERS:
                out = scorer.score(obs_logits, per_logits, chunk)
                # Escribe solo las posiciones aún sin valor: el solapamiento no
                # se promedia, se resuelve por primera escritura, que es la que
                # tiene más contexto por delante.
                for j in range(out.per_token.shape[0]):
                    idx = start + j
                    if idx < n - 1 and torch.isnan(per_token[scorer.name][idx]):
                        per_token[scorer.name][idx] = out.per_token[j]
            if start + _WINDOW >= n:
                break

    return Measurement(
        signals={
            s.name: SignalOutput(s.name, per_token[s.name], s.expected_range) for s in SCORERS
        },
        offsets=offsets,
        n_tokens=n,
    )
