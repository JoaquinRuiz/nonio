"""Ratio observer/cross-perplexity — Binoculars (R-002, FR-002).

Divide la log-perplejidad del texto según el observador entre la
*cross-perplexity*: cuán sorprendentes son las predicciones del performer para el
observador. Ese denominador **es** una medida de la dificultad intrínseca del
texto, que es exactamente lo que pide FR-002: así la prosa naturalmente
predecible —documentación técnica, texto legal— no se confunde con la generada,
que es el sesgo que el Artículo III obliga a combatir.

Valores bajos indican texto poco sorprendente en relación con su propia
dificultad. Se devuelve el ratio negado para que, como en la otra señal, "más
alto" signifique "más señal".
"""

from __future__ import annotations

import torch

from nonio.signals.base import SignalOutput

__all__ = ["Binoculars"]


class Binoculars:
    name = "binoculars"
    expected_range = (-2.0, 0.0)

    def score(
        self,
        observer_logits: torch.Tensor,
        performer_logits: torch.Tensor,
        labels: torch.Tensor,
    ) -> SignalOutput:
        obs = observer_logits[:-1].float()
        per = performer_logits[:-1].float()
        targets = labels[1:]

        obs_logprobs = torch.log_softmax(obs, dim=-1)
        per_logprobs = torch.log_softmax(per, dim=-1)

        # Perplejidad del observador sobre el texto real.
        ppl = -obs_logprobs.gather(-1, targets.unsqueeze(-1)).squeeze(-1)

        # Cross-perplexity: entropía cruzada entre lo que predice el performer y
        # lo que cree el observador, posición a posición.
        x_ppl = -(per_logprobs.exp() * obs_logprobs).sum(dim=-1)

        ratio = ppl / x_ppl.clamp_min(1e-12)
        return SignalOutput(self.name, -ratio, self.expected_range)
